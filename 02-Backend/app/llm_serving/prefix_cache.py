"""Prefix caching for KV cache hit rate optimization."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional

from .kv_cache import KVCacheManager, KVCacheBlock

logger = logging.getLogger(__name__)


@dataclass
class PrefixEntry:
    prefix_hash: str
    blocks: list[KVCacheBlock]
    seq_len: int
    created_at: float
    last_accessed: float
    hit_count: int = 0


class PrefixCache:
    def __init__(
        self,
        kv_manager: KVCacheManager,
        max_entries: int = 1024,
        hash_prefix_length: int = 32,
        ttl_seconds: float = 3600.0,
    ):
        self._kv_manager = kv_manager
        self._max_entries = max_entries
        self._hash_prefix_length = hash_prefix_length
        self._ttl = ttl_seconds
        self._cache: dict[str, PrefixEntry] = {}
        self._hits = 0
        self._misses = 0

    def compute_hash(self, input_ids: list[int]) -> str:
        prefix = input_ids[: self._hash_prefix_length]
        return hashlib.sha256(str(prefix).encode()).hexdigest()

    def get(self, prefix_hash: str, layer_idx: int) -> Optional[list[KVCacheBlock]]:
        entry = self._cache.get(prefix_hash)
        if entry is None:
            self._misses += 1
            return None
        if time.time() - entry.created_at > self._ttl:
            del self._cache[prefix_hash]
            self._misses += 1
            return None
        entry.hit_count += 1
        entry.last_accessed = time.time()
        for block in entry.blocks:
            block.ref_count += 1
        self._hits += 1
        return entry.blocks

    def put(self, prefix_hash: str, blocks: list[KVCacheBlock], seq_len: int) -> None:
        if len(self._cache) >= self._max_entries:
            self._evict()
        for block in blocks:
            block.is_prefix = True
            block.prefix_hash = prefix_hash
            block.ref_count += 1
        entry = PrefixEntry(
            prefix_hash=prefix_hash,
            blocks=blocks,
            seq_len=seq_len,
            created_at=time.time(),
            last_accessed=time.time(),
        )
        self._cache[prefix_hash] = entry

    def invalidate(self, prefix_hash: str) -> None:
        entry = self._cache.pop(prefix_hash, None)
        if entry:
            self._kv_manager.release(entry.blocks)

    def _evict(self) -> None:
        if not self._cache:
            return
        oldest = min(self._cache.values(), key=lambda e: e.last_accessed)
        self._kv_manager.release(oldest.blocks)
        del self._cache[oldest.prefix_hash]

    def metrics(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "entries": len(self._cache),
            "hit_ratio": self._hits / total if total > 0 else 0.0,
            "hits": self._hits,
            "misses": self._misses,
        }
