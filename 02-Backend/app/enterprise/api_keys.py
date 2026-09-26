"""API key management with scopes and rotation."""

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    id: str
    org_id: str
    name: str
    key_hash: str
    scopes: list[str]
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class APIKeyManager:
    def __init__(self):
        self._keys: dict[str, APIKey] = {}

    def create_key(self, org_id: str, name: str, scopes: list[str], expires_at: Optional[str] = None) -> dict:
        key_id = str(uuid.uuid4())
        secret = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(secret.encode()).hexdigest()
        api_key = APIKey(id=key_id, org_id=org_id, name=name, key_hash=key_hash, scopes=scopes, expires_at=expires_at)
        self._keys[key_id] = api_key
        self._persist(api_key)
        return {"key_id": key_id, "secret": secret, "scopes": scopes, "expires_at": expires_at}

    def _persist(self, api_key: APIKey):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO api_keys (id, org_id, name, key_hash, scopes, expires_at, last_used_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    api_key.id,
                    api_key.org_id,
                    api_key.name,
                    api_key.key_hash,
                    json.dumps(api_key.scopes),
                    api_key.expires_at,
                    api_key.last_used_at,
                    api_key.created_at,
                ),
            )
            conn.commit()

    def revoke_key(self, key_id: str) -> bool:
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        with get_db() as conn:
            conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            conn.commit()
        del self._keys[key_id]
        return True

    def rotate_key(self, key_id: str) -> dict:
        api_key = self._keys.get(key_id)
        if not api_key:
            raise ValueError(f"API key {key_id} not found")
        new_secret = secrets.token_urlsafe(32)
        api_key.key_hash = hashlib.sha256(new_secret.encode()).hexdigest()
        self._persist(api_key)
        return {"key_id": key_id, "new_secret": new_secret}

    def list_keys(self, org_id: str) -> list[dict]:
        return [
            {
                "id": k.id,
                "name": k.name,
                "scopes": k.scopes,
                "expires_at": k.expires_at,
                "created_at": k.created_at,
            }
            for k in self._keys.values()
            if k.org_id == org_id
        ]

    def verify_key(self, secret: str) -> Optional[APIKey]:
        key_hash = hashlib.sha256(secret.encode()).hexdigest()
        for api_key in self._keys.values():
            if api_key.key_hash == key_hash:
                api_key.last_used_at = datetime.now(timezone.utc).isoformat()
                self._persist(api_key)
                return api_key
        return None


import json

api_key_manager = APIKeyManager()
