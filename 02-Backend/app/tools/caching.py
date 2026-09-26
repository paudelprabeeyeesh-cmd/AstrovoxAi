"""Tool result caching."""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json


@dataclass
class CachedToolResult:
    cache_key: str
    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    ttl_seconds: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0


class ToolCache:
    _cache: Dict[str, CachedToolResult] = {}
    _max_size = 10000

    @classmethod
    def _compute_key(cls, tool_name: str, parameters: Dict[str, Any]) -> str:
        raw = json.dumps({"tool": tool_name, "params": parameters}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def get(cls, tool_name: str, parameters: Dict[str, Any]) -> Optional[Any]:
        key = cls._compute_key(tool_name, parameters)
        cached = cls._cache.get(key)
        if not cached:
            return None
        age = (datetime.now(timezone.utc) - cached.created_at).total_seconds()
        if age > cached.ttl_seconds:
            del cls._cache[key]
            return None
        cached.hit_count += 1
        return cached.result

    @classmethod
    def put(cls, tool_name: str, parameters: Dict[str, Any], result: Any, ttl_seconds: int = 300) -> None:
        key = cls._compute_key(tool_name, parameters)
        cls._cache[key] = CachedToolResult(
            cache_key=key,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            ttl_seconds=ttl_seconds,
        )
        if len(cls._cache) > cls._max_size:
            oldest = min(cls._cache.values(), key=lambda x: x.created_at)
            del cls._cache[oldest.cache_key]

    @classmethod
    def invalidate(cls, tool_name: str) -> None:
        keys_to_delete = [k for k, v in cls._cache.items() if v.tool_name == tool_name]
        for key in keys_to_delete:
            del cls._cache[key]
