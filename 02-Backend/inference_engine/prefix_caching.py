
import numpy as np
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CacheEntry:
    cache_key: str
    token_ids: Tuple[int, ...]
    kv_data: Optional[np.ndarray]
    hit_count: int = 0
    last_access: float = 0.0
    version: int = 0
    is_valid: bool = True

    def touch(self, timestamp: float):
        self.last_access = timestamp
        self.hit_count += 1


class PrefixCache:
    def __init__(self, max_entries: int = 1024, max_size_bytes: int = 256 * 1024 * 1024):
        self.max_entries = max_entries
        self.max_size_bytes = max_size_bytes
        self.cache: Dict[str, CacheEntry] = {}
        self.lru_order: List[str] = []
        self._timestamp = 0.0
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "invalidations": 0}

    def _hash(self, token_ids: Tuple[int, ...]) -> str:
        return hashlib.sha256(str(token_ids).encode()).hexdigest()[:16]

    def _now(self) -> float:
        self._timestamp += 1.0
        return self._timestamp

    def lookup(self, token_ids: Tuple[int, ...]) -> Optional[Tuple[CacheEntry, int]]:
        cache_key = self._hash(token_ids)
        entry = self.cache.get(cache_key)
        if entry is not None and entry.is_valid:
            entry.touch(self._now())
            self.stats["hits"] += 1
            overlap = len(token_ids)
            return entry, overlap
        self.stats["misses"] += 1
        return None

    def insert(self, token_ids: Tuple[int, ...], kv_data: np.ndarray) -> CacheEntry:
        cache_key = self._hash(token_ids)
        if cache_key in self.cache:
            old = self.cache[cache_key]
            old.kv_data = kv_data.copy()
            old.version += 1
            old.is_valid = True
            old.touch(self._now())
            return old
        self._evict_if_needed(len(token_ids))
        entry = CacheEntry(
            cache_key=cache_key,
            token_ids=token_ids,
            kv_data=kv_data.astype(np.float32).copy(),
        )
        entry.touch(self._now())
        self.cache[cache_key] = entry
        self.lru_order.append(cache_key)
        return entry

    def invalidate(self, token_ids: Tuple[int, ...]):
        cache_key = self._hash(token_ids)
        entry = self.cache.get(cache_key)
        if entry is not None:
            entry.is_valid = False
            self.stats["invalidations"] += 1

    def invalidate_all(self, token_prefix: Tuple[int, ...]):
        for key, entry in list(self.cache.items()):
            if entry.token_ids[:len(token_prefix)] == token_prefix:
                entry.is_valid = False
                self.stats["invalidations"] += 1

    def _evict_if_needed(self, incoming_size: int):
        while (len(self.cache) >= self.max_entries or
               self._estimate_bytes() + incoming_size * 4 > self.max_size_bytes):
            if not self.lru_order:
                break
            victim_key = self.lru_order.pop(0)
            if victim_key in self.cache:
                del self.cache[victim_key]
                self.stats["evictions"] += 1

    def _estimate_bytes(self) -> int:
        total = 0
        for e in self.cache.values():
            if e.kv_data is not None:
                total += e.kv_data.nbytes
        return total

    def find_best_prefix(self, token_ids: Tuple[int, ...]) -> Optional[Tuple[CacheEntry, int]]:
        best_entry = None
        best_len = 0
        for entry in self.cache.values():
            if not entry.is_valid:
                continue
            max_len = min(len(entry.token_ids), len(token_ids))
            match_len = 0
            for i in range(max_len):
                if entry.token_ids[i] == token_ids[i]:
                    match_len += 1
                else:
                    break
            if match_len > best_len:
                best_len = match_len
                best_entry = entry
        if best_entry is not None and best_len > 0:
            best_entry.touch(self._now())
            self.stats["hits"] += 1
            return best_entry, best_len
        self.stats["misses"] += 1
        return None

    def get_stats(self) -> Dict:
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0.0
        return {
            "entries": len(self.cache),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.stats["evictions"],
            "invalidations": self.stats["invalidations"],
            "estimated_bytes": self._estimate_bytes(),
        }
