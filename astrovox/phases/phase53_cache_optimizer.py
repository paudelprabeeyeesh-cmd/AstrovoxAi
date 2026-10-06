"""Computation caching for Astrovox."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """A cached computation result."""
    key: str
    result: any
    size: int = 0


class CacheOptimizer:
    """LRU computation cache."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        data = str((args, sorted(kwargs.items()))).encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def get(self, *args, **kwargs) -> Any | None:
        key = self._make_key(*args, **kwargs)
        entry = self.cache.get(key)
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        return entry.result

    def put(self, key: str, result: Any) -> None:
        if key in self.cache:
            return
        if len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        self.cache[key] = CacheEntry(key=key, result=result)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"size": len(self.cache), "hits": self.hits, "misses": self.misses,
                "hit_rate": self.hits / max(total, 1)}

    def clear(self) -> None:
        self.cache.clear()
        self.hits = 0
        self.misses = 0
