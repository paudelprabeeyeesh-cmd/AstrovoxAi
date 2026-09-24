import time
import threading
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    ttl: float
    tags: Tuple[str, ...] = ()
    hit_count: int = 0


class CacheLayer:
    def __init__(self, max_size: int = 1024, default_ttl: float = 300.0):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._tag_index: Dict[str, Set[str]] = {}

    def _is_expired(self, entry: CacheEntry) -> bool:
        return entry.ttl > 0 and (time.time() - entry.created_at) >= entry.ttl

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, v in self._cache.items() if self._is_expired(v)]
        for k in expired:
            self._remove_entry(k)

    def _evict_lru(self):
        if not self._cache:
            return
        lru_key = min(
            self._cache,
            key=lambda k: (self._cache[k].hit_count, self._cache[k].created_at),
        )
        self._remove_entry(lru_key)
        self._evictions += 1

    def _remove_entry(self, key: str):
        entry = self._cache.pop(key, None)
        if entry:
            for tag in entry.tags:
                idx = self._tag_index.get(tag, set())
                idx.discard(key)
                if not idx:
                    self._tag_index.pop(tag, None)

    def _enforce_max_size(self):
        if len(self._cache) >= self._max_size:
            self._evict_lru()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            self._evict_expired()
            entry = self._cache.get(key)
            if entry is None or self._is_expired(entry):
                if entry and self._is_expired(entry):
                    self._remove_entry(key)
                self._misses += 1
                return default
            entry.hit_count += 1
            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: float = 0,
        tags: Tuple[str, ...] = (),
    ) -> None:
        with self._lock:
            if key not in self._cache:
                self._enforce_max_size()
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl > 0 else self._default_ttl,
                tags=tags,
            )
            for tag in tags:
                self._tag_index.setdefault(tag, set()).add(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def invalidate_by_tag(self, tag: str) -> int:
        with self._lock:
            keys = list(self._tag_index.pop(tag, set()))
            for k in keys:
                self._remove_entry(k)
            return len(keys)

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if self._is_expired(entry):
                self._remove_entry(key)
                return False
            return True

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._tag_index.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    @property
    def size(self) -> int:
        with self._lock:
            self._evict_expired()
            return len(self._cache)

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }

    def set_many(self, items: Dict[str, Tuple[Any, float, Tuple[str, ...]]]):
        for key, (value, ttl, tags) in items.items():
            self.set(key, value, ttl=ttl, tags=tags)

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        return {k: self.get(k) for k in keys}


class CacheLayerProxy:
    def __init__(self, cache: CacheLayer, prefix: str = ""):
        self._cache = cache
        self._prefix = prefix

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(self._k(key), default)

    def set(self, key: str, value: Any, ttl: float = 0, tags: Tuple[str, ...] = ()):
        self._cache.set(self._k(key), value, ttl=ttl, tags=tags)

    def delete(self, key: str) -> bool:
        return self._cache.delete(self._k(key))
