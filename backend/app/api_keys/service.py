"""API key service with rate limiting and usage tracking."""
from __future__ import annotations

import hashlib
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class APIKeyService:
    def __init__(self) -> None:
        self._keys: dict[str, dict] = {}
        self._usage: dict[str, list[dict]] = defaultdict(list)
        self._rate_limits: dict[str, dict] = {}

    def create_key(self, user_id: str, name: str, scopes: list[str] | None = None, expires_in_days: Optional[int] = None) -> dict:
        key = f"astrovox-{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=expires_in_days)) if expires_in_days else None
        record = {
            "id": secrets.token_urlsafe(16),
            "key": key,
            "key_hash": key_hash,
            "user_id": user_id,
            "name": name,
            "scopes": scopes or ["read"],
            "created_at": now,
            "last_used": None,
            "expires_at": expires_at,
            "usage_count": 0,
        }
        self._keys[key_hash] = record
        return record

    def validate_key(self, key: str) -> Optional[dict]:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        record = self._keys.get(key_hash)
        if not record:
            return None
        if record.get("expires_at") and record["expires_at"] < datetime.now(timezone.utc):
            return None
        record["last_used"] = datetime.now(timezone.utc)
        record["usage_count"] += 1
        return record

    def list_keys(self, user_id: str) -> list[dict]:
        return [k for k in self._keys.values() if k["user_id"] == user_id]

    def revoke_key(self, key_id: str, user_id: str) -> bool:
        for key_hash, record in self._keys.items():
            if record["id"] == key_id and record["user_id"] == user_id:
                del self._keys[key_hash]
                return True
        return False

    def track_usage(self, key_id: str, endpoint: str, method: str, status_code: int, latency_ms: float) -> None:
        self._usage[key_id].append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_usage(self, key_id: str, limit: int = 100) -> list[dict]:
        return self._usage.get(key_id, [])[-limit:]

    def check_rate_limit(self, key_id: str, limit: int = 100, window: int = 60) -> bool:
        now = time.time()
        window_start = now - window
        requests = [t for t in self._usage.get(key_id, []) if t["timestamp"] > window_start]
        return len(requests) < limit
