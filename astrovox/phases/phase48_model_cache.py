"""Cached model storage with TTL."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CachedModel:
    """A cached model entry."""
    key: str
    path: str
    size: int
    loaded_at: float = field(default_factory=time.time)
    ttl: float = 86400.0  # 24 hours

    def is_expired(self) -> bool:
        return time.time() > self.loaded_at + self.ttl


class ModelCache:
    """LRU cache for loaded models."""

    def __init__(self, max_size_mb: float = 1024.0):
        self.max_size_mb = max_size_mb
        self.cache: dict[str, CachedModel] = {}
        self.size_mb = 0.0

    def put(self, key: str, path: str, size: int = 0) -> None:
        existing = self.cache.get(key)
        if existing is not None and not existing.is_expired():
            return
        if key in self.cache:
            self.size_mb -= self.cache[key].size / (1024 * 1024)
        self.cache[key] = CachedModel(key=key, path=path, size=size)
        self.size_mb += size / (1024 * 1024)
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        while self.size_mb > self.max_size_mb and self.cache:
            oldest = min(self.cache.values(), key=lambda c: c.loaded_at)
            self.size_mb -= oldest.size / (1024 * 1024)
            del self.cache[oldest.key]

    def get(self, key: str) -> CachedModel | None:
        m = self.cache.get(key)
        if m is None or m.is_expired():
            return None
        return m

    def clear(self) -> None:
        self.cache.clear()
        self.size_mb = 0.0

    def stats(self) -> dict:
        return {"size_mb": round(self.size_mb, 2), "count": len(self.cache),
                "max_size_mb": self.max_size_mb}
