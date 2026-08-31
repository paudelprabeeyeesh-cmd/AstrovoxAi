"""Authorization — Role-Based Access Control (RBAC) and permissions."""

import logging
import functools
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Role(Enum):
    """User roles."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    ORG_ADMIN = "org_admin"
    VIEWER = "viewer"


class Permission(Enum):
    """System permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_ORG = "manage_org"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_API_KEYS = "manage_api_keys"
    ADMIN = "admin"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.VIEWER: [Permission.READ],
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.MODERATOR: [Permission.READ, Permission.WRITE, Permission.DELETE],
    Role.ADMIN: [
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_API_KEYS,
    ],
    Role.ORG_ADMIN: [
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.MANAGE_USERS, Permission.MANAGE_ORG,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_API_KEYS,
    ],
}


@dataclass
class APIKey:
    """API key with scopes."""
    key_id: str
    user_id: str
    name: str
    scopes: list[str]
    created_at: float
    expires_at: float
    is_active: bool = True
    last_used: float = 0.0


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self._user_roles: dict[str, Role] = {}
        self._api_keys: dict[str, APIKey] = {}

    def assign_role(self, user_id: str, role: Role):
        """Assign a role to a user."""
        self._user_roles[user_id] = role

    def get_role(self, user_id: str) -> Role:
        """Get user's role."""
        return self._user_roles.get(user_id, Role.USER)

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has a permission."""
        role = self.get_role(user_id)
        return permission in ROLE_PERMISSIONS.get(role, [])

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check permission, logging if denied."""
        if self.has_permission(user_id, permission):
            return True

        logger.warning(
            "Permission denied: user=%s, permission=%s, role=%s",
            user_id, permission.value, self.get_role(user_id).value,
        )
        return False

    def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str],
        ttl: int = 2592000,
    ) -> APIKey:
        """Create an API key."""
        import secrets

        key_id = f"avx_{secrets.token_urlsafe(32)}"
        now = time.time()

        api_key = APIKey(
            key_id=key_id,
            user_id=user_id,
            name=name,
            scopes=scopes,
            created_at=now,
            expires_at=now + ttl,
        )

        self._api_keys[key_id] = api_key
        return api_key

    def validate_api_key(self, key_id: str) -> Optional[APIKey]:
        """Validate an API key."""
        api_key = self._api_keys.get(key_id)
        if not api_key:
            return None

        if not api_key.is_active or time.time() > api_key.expires_at:
            return None

        api_key.last_used = time.time()
        return api_key

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self._api_keys:
            self._api_keys[key_id].is_active = False
            return True
        return False

    def get_user_api_keys(self, user_id: str) -> list[APIKey]:
        """Get all API keys for a user."""
        return [k for k in self._api_keys.values() if k.user_id == user_id]


import time

rbac_manager = RBACManager()
