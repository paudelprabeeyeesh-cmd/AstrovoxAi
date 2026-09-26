"""Role-Based Access Control (RBAC) with permissions and API key management."""
import time
import secrets
import logging
from typing import Optional, List
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class Role(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    VIEWER = "viewer"


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_API_KEYS = "manage_api_keys"
    ADMIN = "admin"


ROLE_PERMISSIONS = {
    Role.VIEWER: [Permission.READ],
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.MODERATOR: [Permission.READ, Permission.WRITE, Permission.DELETE],
    Role.ADMIN: [
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS,
        Permission.VIEW_ANALYTICS, Permission.MANAGE_API_KEYS,
    ],
}


@dataclass
class APIKey:
    key_id: str
    user_id: str
    name: str
    scopes: List[str]
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 2592000)
    is_active: bool = True
    last_used: float = 0.0


class RBACManager:
    def __init__(self):
        self._user_roles: dict[str, Role] = {}
        self._api_keys: dict[str, APIKey] = {}
        self._lock = __import__('threading').Lock()

    def assign_role(self, user_id: str, role: Role):
        with self._lock:
            self._user_roles[user_id] = role
            logger.info("Assigned role %s to user %s", role.value, user_id)

    def get_role(self, user_id: str) -> Role:
        with self._lock:
            return self._user_roles.get(user_id, Role.USER)

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        role = self.get_role(user_id)
        return permission in ROLE_PERMISSIONS.get(role, [])

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        if self.has_permission(user_id, permission):
            return True
        logger.warning("Permission denied: user=%s permission=%s role=%s", user_id, permission.value, self.get_role(user_id).value)
        return False

    def create_api_key(self, user_id: str, name: str, scopes: List[str], ttl: int = 2592000) -> APIKey:
        key_id = f"avx_{secrets.token_urlsafe(32)}"
        now = time.time()
        api_key = APIKey(
            key_id=key_id, user_id=user_id, name=name, scopes=scopes,
            created_at=now, expires_at=now + ttl,
        )
        with self._lock:
            self._api_keys[key_id] = api_key
        return api_key

    def validate_api_key(self, key_id: str) -> Optional[APIKey]:
        with self._lock:
            api_key = self._api_keys.get(key_id)
        if not api_key or not api_key.is_active or time.time() > api_key.expires_at:
            return None
        api_key.last_used = time.time()
        return api_key

    def revoke_api_key(self, key_id: str) -> bool:
        with self._lock:
            if key_id in self._api_keys:
                self._api_keys[key_id].is_active = False
                return True
        return False

    def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        with self._lock:
            return [k for k in self._api_keys.values() if k.user_id == user_id]


rbac_manager = RBACManager()
