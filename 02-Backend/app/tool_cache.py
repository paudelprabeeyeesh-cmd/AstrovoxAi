"""Tool result caching layer with TTL and invalidation."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class CachedToolResult:
    tool_name: str
    arguments_hash: str
    result: str
    cached_at: float = field(default_factory=time.time)
    ttl_seconds: int = 300
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.cached_at > self.ttl_seconds

    @property
    def cache_key(self) -> str:
        return f"tool:cache:{self.tool_name}:{self.arguments_hash}"


class ToolCache:
    def __init__(self, default_ttl: int = 300, max_size: int = 10000):
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._local_cache: Dict[str, CachedToolResult] = {}

    def _compute_hash(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        payload = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def get(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        key = self._compute_hash(tool_name, arguments)
        local = self._local_cache.get(key)
        if local and not local.is_expired:
            local.hit_count += 1
            logger.debug("Tool cache hit for %s", tool_name)
            return local.result
        if local:
            del self._local_cache[key]
        try:
            data = cache.get(key)
            if data is not None:
                logger.debug("Tool cache hit (redis) for %s", tool_name)
                return data
        except Exception as _e:  # noqa: BLE001
            pass
        return None

    def set(self, tool_name: str, arguments: Dict[str, Any], result: str, ttl: Optional[int] = None) -> None:
        key = self._compute_hash(tool_name, arguments)
        ttl = ttl or self._default_ttl
        entry = CachedToolResult(
            tool_name=tool_name,
            arguments_hash=key,
            result=result,
            ttl_seconds=ttl,
        )
        if len(self._local_cache) >= self._max_size:
            oldest = min(self._local_cache.values(), key=lambda x: x.cached_at)
            del self._local_cache[oldest.arguments_hash]
        self._local_cache[key] = entry
        try:
            cache.set(key, result, ttl=ttl)
        except Exception as _e:  # noqa: BLE001
            pass
        logger.debug("Tool cache set for %s (ttl=%ds)", tool_name, ttl)

    def invalidate(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> None:
        if arguments is not None:
            key = self._compute_hash(tool_name, arguments)
            self._local_cache.pop(key, None)
            try:
                cache.delete(key)
            except Exception as _e:  # noqa: BLE001
                pass
        else:
            prefix = f"tool:cache:{tool_name}:"
            to_delete = [k for k in self._local_cache if k.startswith(prefix)]
            for k in to_delete:
                del self._local_cache[k]
            try:
                import redis
                r = cache._redis
                if r:
                    pattern = f"*{prefix}*"
                    for k in r.scan_iter(match=pattern, count=1000):
                        r.delete(k)
            except Exception as _e:  # noqa: BLE001
                pass

    def clear(self) -> None:
        self._local_cache.clear()
        try:
            if cache._redis:
                for key in cache._redis.scan_iter(match="tool:cache:*", count=1000):
                    cache._redis.delete(key)
        except Exception as _e:  # noqa: BLE001
            pass

    def get_stats(self) -> Dict[str, Any]:
        total = sum(e.hit_count for e in self._local_cache.values())
        return {
            "local_entries": len(self._local_cache),
            "total_hits": total,
            "max_size": self._max_size,
            "default_ttl": self._default_ttl,
        }


tool_cache = ToolCache()
