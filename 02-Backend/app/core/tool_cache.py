"""Tool result caching layer."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    result: Any
    latency_ms: float
    created_at: float
    hits: int = 0


class ToolCache:
    """In-memory and Redis-backed cache for tool results."""

    def __init__(self, redis_client=None, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self._memory: Dict[str, CacheEntry] = {}

    def _make_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        payload = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        key = self._make_key(tool_name, arguments)
        entry = self._get_entry(key)
        if entry is None:
            return None
        entry.hits += 1
        logger.debug("Tool cache hit for %s (hits=%d)", tool_name, entry.hits)
        return entry.result

    def _get_entry(self, key: str) -> Optional[CacheEntry]:
        if self.redis:
            raw = self.redis.get(key)
            if raw:
                try:
                    data = json.loads(raw)
                    return CacheEntry(**data)
                except Exception:  # noqa: BLE001
                    return None
        return self._memory.get(key)

    def set(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        latency_ms: float,
        ttl: Optional[int] = None,
    ) -> None:
        key = self._make_key(tool_name, arguments)
        entry = CacheEntry(result=result, latency_ms=latency_ms, created_at=__import__("time").time())
        payload = json.dumps(entry.__dict__, default=str)
        if self.redis:
            try:
                self.redis.set(key, payload, ex=ttl or self.default_ttl)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Redis cache set failed: %s", exc)
                self._memory[key] = entry
        else:
            self._memory[key] = entry

    def invalidate(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> None:
        if arguments is not None:
            key = self._make_key(tool_name, arguments)
            self._memory.pop(key, None)
            if self.redis:
                try:
                    self.redis.delete(key)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Redis cache delete failed: %s", exc)
        else:
            prefix = hashlib.sha256(json.dumps({"tool": tool_name, "args": {}}, sort_keys=True).encode()).hexdigest()[:16]
            keys = [k for k in self._memory if k.startswith(prefix)]
            for k in keys:
                self._memory.pop(k, None)
            if self.redis:
                try:
                    self.redis.delete(*keys)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Redis cache bulk delete failed: %s", exc)

    def clear(self) -> None:
        self._memory.clear()
        if self.redis:
            try:
                self.redis.flushdb()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Redis cache flush failed: %s", exc)

    def stats(self) -> Dict[str, Any]:
        total = len(self._memory)
        hits = sum(e.hits for e in self._memory.values())
        return {"size": total, "hits": hits, "misses": total - hits if total else 0}
