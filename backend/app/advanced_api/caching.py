"""API caching layer."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachePolicy:
    ttl_seconds: float = 300.0
    max_size: int = 1000


class APICache:
    def __init__(self, policy: Optional[CachePolicy] = None):
        self.policy = policy or CachePolicy()
        self._store: Dict[str, tuple[Any, float]] = {}

    def _make_key(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> str:
        raw = json.dumps({"method": method, "path": path, "body": body or {}}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        key = self._make_key(method, path, body)
        entry = self._store.get(key)
        if entry and time.time() - entry[1] < self.policy.ttl_seconds:
            return entry[0]
        self._store.pop(key, None)
        return None

    def set(self, method: str, path: str, value: Any, body: Optional[Dict[str, Any]] = None) -> None:
        key = self._make_key(method, path, body)
        self._store[key] = (value, time.time())
        if len(self._store) > self.policy.max_size:
            oldest = min(self._store.items(), key=lambda item: item[1][1])
            self._store.pop(oldest[0])


api_cache = APICache()
