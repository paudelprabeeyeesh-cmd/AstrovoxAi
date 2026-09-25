import uuid
from enum import Enum
from typing import List
from fastapi import Depends, HTTPException

from ..services.auth.auth import get_current_user
from ..repositories.database.client import get_db


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


ROLE_PERMISSIONS = {
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
    Role.ENTERPRISE: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
}


def has_permission(user_id: str, permission: str, resource: str) -> bool:
    try:
        perm = Permission(permission)
    except ValueError:
        return False
    role = get_user_role(user_id)
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    return perm in ROLE_PERMISSIONS.get(role_enum, [])


def get_user_role(user_id: str) -> str:
    if isinstance(user_id, dict):
        user_id = user_id.get("user_id") or user_id.get("sub") or next(iter(user_id.values()))
    with get_db() as conn:
        row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return Role.USER.value
        return row["role"] or Role.USER.value


def require_permission(permission: str, resource: str):
    def _checker(user_id: str = Depends(get_current_user)) -> str:
        if not has_permission(user_id, permission, resource):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user_id
    return _checker
