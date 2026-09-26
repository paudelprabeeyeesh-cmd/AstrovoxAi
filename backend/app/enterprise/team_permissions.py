"""Team permissions and RBAC."""

import logging
from typing import Any, Dict, List, Optional

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
        self._members: Dict[str, Dict[str, str]] = {}

    def register_member(self, org_id: str, user_id: str, role: str = "member") -> None:
        self._members.setdefault(org_id, {})[user_id] = role

    def assign_role(self, org_id: str, user_id: str, role: str) -> dict:
        if role not in self._roles:
            raise ValueError(f"Unknown role: {role}")
        self._members.setdefault(org_id, {})[user_id] = role
        logger.info("Assigned role %s to %s in %s", role, user_id, org_id)
        return {"org_id": org_id, "user_id": user_id, "role": role}

    def check_permission(self, user_id: str, org_id: str, permission: str) -> bool:
        role = self._members.get(org_id, {}).get(user_id)
        if not role:
            return False
        return permission in self._roles.get(role, [])

    def list_permissions(self, org_id: str) -> List[dict]:
        return [
            {
                "user_id": user_id,
                "role": role,
                "permissions": self._roles.get(role, []),
            }
            for user_id, role in self._members.get(org_id, {}).items()
        ]


permission_manager = PermissionManager()
