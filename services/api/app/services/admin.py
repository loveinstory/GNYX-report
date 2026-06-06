from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.database import connect, dict_from_row
from app.services.crypto import decrypt_secret, encrypt_secret


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_credential(provider: str, label: str, value: str) -> dict[str, str]:
    credential_id = f"credential:{provider}:{uuid.uuid4().hex[:8]}"
    timestamp = now_iso()
    encrypted_value = encrypt_secret(value)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO credentials (
              credential_id, provider, label, encrypted_value, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (credential_id, provider, label, encrypted_value, timestamp, timestamp),
        )
    return {"credential_id": credential_id, "provider": provider, "label": label}


def list_credentials() -> list[dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT credential_id, provider, label, created_at, updated_at
            FROM credentials
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict_from_row(row) or {} for row in rows]


def get_latest_credential(provider: str) -> dict[str, str] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT credential_id, provider, label, encrypted_value, created_at, updated_at
            FROM credentials
            WHERE provider = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (provider,),
        ).fetchone()
    credential = dict_from_row(row)
    if credential is None:
        return None
    credential["value"] = decrypt_secret(credential.pop("encrypted_value"))
    return credential


def create_backup() -> dict[str, str]:
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = settings.backup_dir / f"{backup_id}.db"
    if settings.database_path.exists():
        shutil.copy2(settings.database_path, backup_path)
    else:
        Path(backup_path).write_bytes(b"")
    return {"backup_id": backup_id, "path": str(backup_path)}
