"""Authentication and authorization module."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class User:
    id: str
    email: str
    name: str
    created_at: str
    is_active: bool = True
    is_verified: bool = False
    mfa_enabled: bool = False


class AuthManager:
    """Authentication and authorization manager."""

    def __init__(self) -> None:
        self._config = get_config()
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, str] = {}

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        return hmac.compare_digest(self.hash_password(password), hashed)

    def create_user(self, email: str, password: str, name: str) -> User:
        user_id = secrets.token_hex(16)
        user = User(
            id=user_id,
            email=email,
            name=name,
            created_at=datetime.utcnow().isoformat(),
        )
        self._users[user_id] = user
        logger.info(f"Created user: {user_id}")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def generate_api_key(self, user_id: str) -> str:
        key = f"ak_{secrets.token_hex(32)}"
        self._api_keys[key] = user_id
        return key

    def validate_api_key(self, key: str) -> Optional[User]:
        user_id = self._api_keys.get(key)
        if user_id:
            return self._users.get(user_id)
        return None


_auth: Optional[AuthManager] = None


def get_auth() -> AuthManager:
    global _auth
    if _auth is None:
        _auth = AuthManager()
    return _auth
