"""Scoped API key management."""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import secrets
import hashlib


@dataclass
class APIKey:
    key_id: str
    key_hash: str
    user_id: str
    name: str
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    revoked: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class APIKeyManager:
    _keys: Dict[str, APIKey] = {}
    _hash_to_id: Dict[str, str] = {}

    @classmethod
    def create_key(cls, user_id: str, name: str, scopes: List[str], expires_days: Optional[int] = None) -> tuple[str, APIKey]:
        raw_key = f"av_{secrets.token_urlsafe(48)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = secrets.token_urlsafe(16)
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            scopes=scopes,
            expires_at=expires_at,
        )
        cls._keys[key_id] = api_key
        cls._hash_to_id[key_hash] = key_id
        return raw_key, api_key

    @classmethod
    def validate(cls, raw_key: str) -> Optional[APIKey]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = cls._hash_to_id.get(key_hash)
        if not key_id:
            return None
        api_key = cls._keys.get(key_id)
        if not api_key or api_key.revoked:
            return None
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None
        api_key.last_used = datetime.now(timezone.utc)
        return api_key

    @classmethod
    def revoke(cls, key_id: str) -> None:
        api_key = cls._keys.get(key_id)
        if api_key:
            api_key.revoked = True

    @classmethod
    def list_keys(cls, user_id: str) -> List[APIKey]:
        return [k for k in cls._keys.values() if k.user_id == user_id and not k.revoked]
