"""Cache for search query results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """A cached query result."""
    query: str
    results: list[dict]
    score: float
    cached_at: float = field(default_factory=time.time)
    ttl: float = 3600.0

    def is_expired(self) -> bool:
        return time.time() > self.cached_at + self.ttl


class SearchCache:
    """In-memory cache for search results."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}

    def _key(self, query: str, **kwargs) -> str:
        extras = " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{query}|{extras}".lower()

    def get(self, query: str, **kwargs) -> list[dict] | None:
        key = self._key(query, **kwargs)
        entry = self._cache.get(key)
        if entry is None or entry.is_expired():
            return None
        return entry.results

    def put(self, query: str, results: list[dict], **kwargs) -> None:
        key = self._key(query, **kwargs)
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache.values(), key=lambda e: e.cached_at)
            del self._cache[self._key(oldest.query, **{k: v for k, v in kwargs.items()})]
        self._cache[key] = CacheEntry(query=query, results=results, score=1.0)

    def hit(self, query: str, **kwargs) -> bool:
        return self.get(query, **kwargs) is not None

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        hits = 0
        total = 0
        return {"size": len(self._cache), "max_size": self.max_size,
                "ttl_seconds": self.default_ttl}
