"""Team permissions and RBAC."""

import logging

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


class PermissionManager:
    def __init__(self):
        self._roles = {
            "owner": ["read", "write", "admin", "billing", "team_manage"],
            "admin": ["read", "write", "team_manage"],
            "manager": ["read", "write"],
            "member": ["read"],
            "guest": [],
        }

    def assign_role(self, org_id: str, user_id: str, role: str) -> dict:
        if role not in self._roles:
            raise ValueError(f"Unknown role: {role}")
        with get_db() as conn:
            conn.execute(
                "UPDATE organization_members SET role = ? WHERE org_id = ? AND user_id = ?",
                (role, org_id, user_id),
            )
            conn.commit()
        return {"org_id": org_id, "user_id": user_id, "role": role}

    def check_permission(self, user_id: str, org_id: str, permission: str) -> bool:
        with get_db() as conn:
            row = conn.execute(
                "SELECT role FROM organization_members WHERE org_id = ? AND user_id = ?",
                (org_id, user_id),
            ).fetchone()
        if not row:
            return False
        role = row["role"]
        return permission in self._roles.get(role, [])

    def list_permissions(self, org_id: str) -> list[dict]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT user_id, role FROM organization_members WHERE org_id = ?",
                (org_id,),
            ).fetchall()
        return [
            {
                "user_id": r["user_id"],
                "role": r["role"],
                "permissions": self._roles.get(r["role"], []),
            }
            for r in rows
        ]


permission_manager = PermissionManager()
