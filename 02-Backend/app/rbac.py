import logging
from enum import Enum
from typing import List, Dict
from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE = "manage"
    INVITE = "invite"
    BILLING = "billing"
    AUDIT = "audit"
    COMPLIANCE = "compliance"


ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.MANAGE, Permission.INVITE],
    Role.ENTERPRISE: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.MANAGE, Permission.INVITE, Permission.BILLING, Permission.AUDIT, Permission.COMPLIANCE],
    Role.SUPER_ADMIN: list(Permission),
}

RESOURCE_PERMISSIONS: Dict[str, List[Permission]] = {
    "users": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.MANAGE],
    "organizations": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.MANAGE, Permission.INVITE],
    "workspaces": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.MANAGE, Permission.INVITE],
    "billing": [Permission.READ, Permission.WRITE, Permission.BILLING],
    "audit": [Permission.READ, Permission.AUDIT],
    "compliance": [Permission.READ, Permission.WRITE, Permission.COMPLIANCE],
}


def get_user_role(user_id: str) -> str:
    if isinstance(user_id, dict):
        user_id = user_id.get("user_id") or user_id.get("sub") or next(iter(user_id.values()))
    try:
        from repositories.database.client import get_db
        with get_db() as conn:
            row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return Role.USER.value
            return row["role"] or Role.USER.value
    except Exception:
        return Role.USER.value


def has_permission(user_id: str, permission: str, resource: str = "") -> bool:
    try:
        perm = Permission(permission)
    except ValueError:
        return False
    role = get_user_role(user_id)
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    role_perms = ROLE_PERMISSIONS.get(role_enum, [])
    if perm in role_perms:
        return True
    if resource and resource in RESOURCE_PERMISSIONS:
        return perm in RESOURCE_PERMISSIONS[resource]
    return False


def has_org_permission(user_id: str, org_id: str, permission: str) -> bool:
    try:
        from app.organizations import get_user_org_role
        role = get_user_org_role(user_id, org_id)
        if not role:
            return False
        role_enum = Role(role)
        return Permission(permission) in ROLE_PERMISSIONS.get(role_enum, [])
    except Exception:
        return False


def require_permission(permission: str, resource: str = ""):
    def _checker(user_id: str = Depends(get_current_user)) -> str:
        if not has_permission(user_id, permission, resource):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user_id
    return _checker


def get_current_user():
    from services.auth.auth import get_current_user as _get_current_user
    return _get_current_user
