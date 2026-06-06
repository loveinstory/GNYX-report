from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request

from app.db.database import connect, dict_from_row
from app.services.authz import ADMIN, ROLE_LABELS


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Awk@2026!"
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
SESSION_HOURS = 12


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_default_admin() -> None:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
        if row and int(row["total"]) > 0:
            return
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO users (
              user_id, username, display_name, password_hash, role, is_active,
              last_login_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"user_{uuid.uuid4().hex[:12]}",
                DEFAULT_ADMIN_USERNAME,
                "系统管理员",
                hash_password(DEFAULT_ADMIN_PASSWORD),
                ADMIN,
                1,
                None,
                timestamp,
                timestamp,
            ),
        )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = stored_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def list_users() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [_user_row_to_public(row) for row in rows]


def create_user(
    *,
    username: str,
    display_name: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> dict[str, Any]:
    normalized_username = username.strip()
    normalized_password = password.strip()
    if not normalized_username:
        raise ValueError("账号不能为空。")
    if len(normalized_password) < 8:
        raise ValueError("密码至少需要 8 位。")
    _validate_role(role)
    timestamp = now_iso()
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                  user_id, username, display_name, password_hash, role, is_active,
                  last_login_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    normalized_username,
                    display_name.strip() or normalized_username,
                    hash_password(normalized_password),
                    role,
                    1 if is_active else 0,
                    None,
                    timestamp,
                    timestamp,
                ),
            )
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise ValueError("账号已存在。") from exc
        raise
    return get_user_by_id(user_id)


def update_user(
    user_id: str,
    *,
    actor_user_id: str,
    display_name: str | None = None,
    password: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    user = get_user_by_id(user_id)
    normalized_password = password.strip() if password is not None else None
    next_role = role if role is not None else user["role"]
    next_is_active = is_active if is_active is not None else bool(user["is_active"])
    if role is not None:
        _validate_role(role)
    if normalized_password is not None and normalized_password and len(normalized_password) < 8:
        raise ValueError("密码至少需要 8 位。")
    if user_id == actor_user_id and not next_is_active:
        raise ValueError("不能停用当前登录账号。")
    if _would_remove_last_admin(user_id, next_role, next_is_active):
        raise ValueError("至少需要保留一个启用状态的管理员账号。")

    updates: list[str] = []
    params: list[Any] = []
    if display_name is not None:
        updates.append("display_name = ?")
        params.append(display_name.strip() or user["username"])
    if normalized_password:
        updates.append("password_hash = ?")
        params.append(hash_password(normalized_password))
    if role is not None:
        updates.append("role = ?")
        params.append(role)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if is_active else 0)
    if not updates:
        return user

    updates.append("updated_at = ?")
    params.append(now_iso())
    params.append(user_id)
    with connect() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", params)
        if is_active is False:
            conn.execute("UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now_iso(), user_id))
    return get_user_by_id(user_id)


def delete_user(user_id: str, *, actor_user_id: str) -> dict[str, str]:
    user = get_user_by_id(user_id)
    if user_id == actor_user_id:
        raise ValueError("不能删除当前登录账号。")
    if _would_remove_last_admin(user_id, "", False):
        raise ValueError("至少需要保留一个启用状态的管理员账号。")

    with connect() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    return {"status": "succeeded", "user_id": user_id, "username": str(user["username"])}


def get_user_by_id(user_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    user = dict_from_row(row)
    if user is None:
        raise KeyError(user_id)
    return _user_dict_to_public(user)


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    normalized_username = username.strip()
    normalized_password = password.strip()
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (normalized_username,)).fetchone()
        user = dict_from_row(row)
        if user is None or not int(user["is_active"]):
            return None
        if not verify_password(normalized_password, str(user["password_hash"])):
            return None
        timestamp = now_iso()
        conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?", (timestamp, timestamp, user["user_id"]))
    return get_user_by_id(str(user["user_id"]))


def create_session(user_id: str) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    timestamp = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (session_id, user_id, token_hash, expires_at, created_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"session_{uuid.uuid4().hex[:12]}",
                user_id,
                token_hash(token),
                expires_at,
                timestamp,
                None,
            ),
        )
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at}


def login(username: str, password: str) -> dict[str, Any] | None:
    user = authenticate(username, password)
    if user is None:
        return None
    session = create_session(user["user_id"])
    return {**session, "user": user}


def revoke_session(token: str) -> None:
    if not token:
        return
    with connect() as conn:
        conn.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (now_iso(), token_hash(token)),
        )


def get_user_from_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    current_time = now_iso()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT users.*
              FROM auth_sessions
              JOIN users ON users.user_id = auth_sessions.user_id
             WHERE auth_sessions.token_hash = ?
               AND auth_sessions.revoked_at IS NULL
               AND auth_sessions.expires_at > ?
               AND users.is_active = 1
            """,
            (token_hash(token), current_time),
        ).fetchone()
    user = dict_from_row(row)
    return _user_dict_to_public(user) if user else None


def get_user_from_request(request: Request) -> dict[str, Any] | None:
    token = _bearer_token(request)
    return get_user_from_token(token) if token else None


def token_from_request(request: Request) -> str:
    return _bearer_token(request) or ""


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _validate_role(role: str) -> None:
    if role not in ROLE_LABELS:
        raise ValueError("角色不存在。")


def _would_remove_last_admin(user_id: str, next_role: str, next_is_active: bool) -> bool:
    if next_role == ADMIN and next_is_active:
        return False
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM users WHERE role = ? AND is_active = 1 AND user_id <> ?",
            (ADMIN, user_id),
        ).fetchone()
    return int(row["total"]) == 0 if row else True


def _user_row_to_public(row: Any) -> dict[str, Any]:
    return _user_dict_to_public(dict_from_row(row) or {})


def _user_dict_to_public(user: dict[str, Any]) -> dict[str, Any]:
    role = str(user.get("role") or "")
    return {
        "user_id": user.get("user_id", ""),
        "username": user.get("username", ""),
        "display_name": user.get("display_name", ""),
        "role": role,
        "role_label": ROLE_LABELS.get(role, role),
        "is_active": bool(user.get("is_active")),
        "last_login_at": user.get("last_login_at") or "",
        "created_at": user.get("created_at", ""),
        "updated_at": user.get("updated_at", ""),
    }
