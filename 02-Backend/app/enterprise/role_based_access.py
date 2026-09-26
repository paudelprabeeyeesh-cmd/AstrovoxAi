from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class RoleBasedAccess:
    def __init__(self):
        self.roles: Dict[str, List[str]] = {
            "admin": ["read", "write", "delete", "manage_users", "manage_tenants"],
            "editor": ["read", "write"],
            "viewer": ["read"],
        }
        self.user_roles: Dict[str, str] = {}

    def assign_role(self, user_id: str, role: str) -> None:
        if role not in self.roles:
            raise ValueError(f"Unknown role: {role}")
        self.user_roles[user_id] = role
        logger.info("Assigned role %s to user %s", role, user_id)

    def has_permission(self, user_id: str, permission: str) -> bool:
        role = self.user_roles.get(user_id, "viewer")
        return permission in self.roles.get(role, [])

    def get_user_role(self, user_id: str) -> str:
        return self.user_roles.get(user_id, "viewer")
