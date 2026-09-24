"""Multi-tier caching and cache warming."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheLevel:
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: float
    created: float = field(default_factory=time.time)

    def expired(self) -> bool:
        return time.time() - self.created >= self.ttl


class MultiTierCache:
    def __init__(self) -> None:
        self._stores: Dict[str, Dict[str, CacheEntry]] = {CacheLevel.L1: {}, CacheLevel.L2: {}, CacheLevel.L3: {}}
        self._lock = threading.Lock()
        self._hits: Dict[str, int] = {CacheLevel.L1: 0, CacheLevel.L2: 0, CacheLevel.L3: 0}
        self._misses: Dict[str, int] = {CacheLevel.L1: 0, CacheLevel.L2: 0, CacheLevel.L3: 0}

    def _get_entry(self, store: Dict[str, CacheEntry], key: str) -> Optional[CacheEntry]:
        entry = store.get(key)
        if entry is None:
            return None
        if entry.expired():
            store.pop(key, None)
            return None
        return entry

    def _maybe_promote(self, key: str, value: Any, ttl: float) -> None:
        now = time.time()
        entry = CacheEntry(key=key, value=value, ttl=ttl, created=now)
        for level in [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]:
            self._stores[level][key] = entry

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            for level in [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]:
                entry = self._get_entry(self._stores[level], key)
                if entry is not None:
                    self._hits[level] += 1
                    if level != CacheLevel.L1:
                        self._stores[CacheLevel.L1][key] = entry
                    return entry.value
                self._misses[level] += 1
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._maybe_promote(key, value, ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            for level in [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]:
                self._stores[level].pop(key, None)

    def clear(self) -> None:
        with self._lock:
            for level in [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]:
                self._stores[level].clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_hits = sum(self._hits.values())
            total_misses = sum(self._misses.values())
            return {
                "hits_by_level": dict(self._hits),
                "misses_by_level": dict(self._misses),
                "total_hits": total_hits,
                "total_misses": total_misses,
                "hit_rate": total_hits / max(total_hits + total_misses, 1),
            }


class CacheWarming:
    def __init__(self, cache: MultiTierCache) -> None:
        self._cache = cache
        self._strategies: List[Callable[[], List[tuple]]] = []
        self._lock = threading.Lock()

    def register(self, strategy: Callable[[], List[tuple]]) -> None:
        with self._lock:
            self._strategies.append(strategy)

    def warm(self) -> Dict[str, Any]:
        warmed = 0
        errors = 0
        with self._lock:
            for strategy in self._strategies:
                try:
                    for key, value, ttl in strategy():
                        self._cache.set(key, value, ttl)
                        warmed += 1
                except Exception as exc:
                    logger.error("cache warming strategy failed: %s", exc)
                    errors += 1
        return {"warmed": warmed, "errors": errors}

    def status(self) -> Dict[str, Any]:
        return {"strategies_registered": len(self._strategies), "cache_stats": self._cache.stats()}
