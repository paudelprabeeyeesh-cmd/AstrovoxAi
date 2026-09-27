"""
API key management for AstrovoxAI.
Handles key creation, scoping, rotation, and revocation.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class APIKeyScope(str, Enum):
    INFERENCE = "inference"
    EMBEDDINGS = "embeddings"
    FINE_TUNING = "fine_tuning"
    ANALYTICS = "analytics"
    ADMIN = "admin"
    READ_ONLY = "read_only"


@dataclass
class APIKey:
    key_id: str
    developer_id: str
    name: str
    prefix: str
    hashed_key: str
    scopes: List[APIKeyScope]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        if self.revoked_at:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        data = {
            "key_id": self.key_id,
            "developer_id": self.developer_id,
            "name": self.name,
            "prefix": self.prefix,
            "scopes": [s.value for s in self.scopes],
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
        return data


class APIKeyManager:
    """Manages API key lifecycle."""

    def __init__(self):
        self._keys: Dict[str, APIKey] = {}

    def create_key(
        self,
        developer_id: str,
        name: str,
        scopes: Optional[List[APIKeyScope]] = None,
        expires_in_days: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        raw_key = f"avx_{secrets.token_urlsafe(32)}"
        prefix = raw_key[:8]
        key = APIKey(
            key_id=str(uuid.uuid4()),
            developer_id=developer_id,
            name=name,
            prefix=prefix,
            hashed_key=raw_key,
            scopes=scopes or [APIKeyScope.INFERENCE],
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
        )
        self._keys[key.key_id] = key
        logger.info("Created API key %s for developer %s", key.key_id, developer_id)
        return key, raw_key

    def get_key(self, key_id: str) -> Optional[APIKey]:
        return self._keys.get(key_id)

    def get_key_by_prefix(self, prefix: str) -> Optional[APIKey]:
        for key in self._keys.values():
            if key.prefix == prefix and key.is_valid():
                return key
        return None

    def list_keys(self, developer_id: str) -> List[APIKey]:
        return [k for k in self._keys.values() if k.developer_id == developer_id]

    def revoke_key(self, key_id: str) -> None:
        key = self._keys.get(key_id)
        if key:
            key.revoked_at = datetime.utcnow()
            logger.info("Revoked API key %s", key_id)

    def rotate_key(self, key_id: str) -> tuple[APIKey, str]:
        old_key = self._keys.get(key_id)
        if not old_key:
            raise ValueError("Key not found")
        self.revoke_key(key_id)
        return self.create_key(
            developer_id=old_key.developer_id,
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
        )

    def record_usage(self, key_id: str) -> None:
        key = self._keys.get(key_id)
        if key:
            key.last_used_at = datetime.utcnow()
