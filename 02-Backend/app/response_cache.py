"""HTTP response cache with tag-based invalidation for AstrovoxAI."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.distributed_cache import distributed_cache

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    status_code: int
    headers: Dict[str, str]
    body: Any
    created_at: float
    ttl: float

    @property
    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


class ResponseCache:
    """HTTP response cache with TTL and tag-based invalidation."""

    def __init__(self, default_ttl: float = 60.0, max_entries: int = 4096):
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._tags: Dict[str, List[str]] = {}

    def _make_key(self, method: str, path: str, params: Dict[str, Any], user_id: Optional[str] = None) -> str:
        raw = f"{method}:{path}:{sorted((params or {}).items())}:{user_id or 'anon'}"
        return f"http:cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def get(self, method: str, path: str, params: Dict[str, Any], user_id: Optional[str] = None) -> Optional[CachedResponse]:
        key = self._make_key(method, path, params, user_id)
        data = distributed_cache.get(key)
        if data is None:
            return None
        entry = CachedResponse(
            status_code=data["status_code"],
            headers=data.get("headers", {}),
            body=data["body"],
            created_at=data["created_at"],
            ttl=data.get("ttl", self.default_ttl),
        )
        if entry.expired:
            self.invalidate(key)
            return None
        return entry

    def set(
        self,
        method: str,
        path: str,
        params: Dict[str, Any],
        status_code: int,
        headers: Dict[str, str],
        body: Any,
        ttl: Optional[float] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        key = self._make_key(method, path, params, user_id)
        data = {
            "status_code": status_code,
            "headers": headers,
            "body": body,
            "created_at": time.time(),
            "ttl": ttl or self.default_ttl,
        }
        distributed_cache.set(key, data, ttl=int(ttl or self.default_ttl), tags=tags)
        if tags:
            for tag in tags:
                self._tags.setdefault(tag, []).append(key)

    def invalidate(self, key: str) -> bool:
        return distributed_cache.delete(key)

    def invalidate_tags(self, tags: List[str]) -> int:
        total = 0
        for tag in tags:
            total += distributed_cache.invalidate_tag(tag)
            self._tags.pop(tag, None)
        return total

    def invalidate_prefix(self, prefix: str) -> int:
        return distributed_cache.invalidate_prefix(f"http:cache:{prefix}")

    def stats(self) -> Dict[str, Any]:
        return {
            **distributed_cache.stats(),
            "tagged_keys": sum(len(v) for v in self._tags.values()),
        }


response_cache = ResponseCache()
