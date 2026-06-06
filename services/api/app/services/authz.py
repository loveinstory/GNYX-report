from __future__ import annotations

from fastapi import HTTPException, Request


ADMIN = "admin"
CUSTOMER_SERVICE = "customer_service"
INSPECTOR = "inspector"

ROLE_LABELS = {
    ADMIN: "管理员",
    CUSTOMER_SERVICE: "客服",
    INSPECTOR: "检测",
}


def current_role(request: Request) -> str:
    return current_user(request)["role"]


def current_user(request: Request) -> dict[str, str]:
    from app.services.accounts import get_user_from_request

    user = get_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录平台。")
    return user


def require_authenticated(request: Request) -> dict[str, str]:
    return current_user(request)


def require_role(request: Request, allowed_roles: set[str]) -> str:
    user = current_user(request)
    role = user["role"]
    if ADMIN in allowed_roles and role == ADMIN:
        return role
    if role not in allowed_roles:
        allowed = "、".join(ROLE_LABELS[item] for item in allowed_roles if item in ROLE_LABELS)
        raise HTTPException(status_code=403, detail=f"当前角色无权限执行该操作，允许角色：{allowed}")
    return role
