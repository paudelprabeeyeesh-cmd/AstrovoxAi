"""Production KV cache with prefix caching and compression."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import torch

logger = logging.getLogger(__name__)


@dataclass
class KVCacheBlock:
    block_id: int
    layer_idx: int
    k: torch.Tensor
    v: torch.Tensor
    ref_count: int = 1
    last_accessed: float = field(default_factory=time.time)
    is_prefix: bool = False
    prefix_hash: Optional[str] = None


class KVCacheManager:
    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        max_batch_size: int,
        max_seq_len: int,
        device: torch.device,
        dtype: torch.dtype = torch.float16,
        block_size: int = 16,
        max_cache_blocks: int = 4096,
        eviction_policy: str = "lru",
    ):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.device = device
        self.dtype = dtype
        self.block_size = block_size
        self.max_cache_blocks = max_cache_blocks
        self.eviction_policy = eviction_policy
        self._blocks: dict[int, KVCacheBlock] = {}
        self._free_list: list[int] = []
        self._next_block_id = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def allocate(self, layer_idx: int, seq_len: int, is_prefix: bool = False, prefix_hash: Optional[str] = None) -> list[KVCacheBlock]:
        num_blocks = (seq_len + self.block_size - 1) // self.block_size
        blocks: list[KVCacheBlock] = []
        for _ in range(num_blocks):
            block = self._get_free_block(layer_idx, is_prefix, prefix_hash)
            blocks.append(block)
        return blocks

    def _get_free_block(self, layer_idx: int, is_prefix: bool, prefix_hash: Optional[str]) -> KVCacheBlock:
        if self._free_list:
            block_id = self._free_list.pop()
            block = self._blocks[block_id]
            block.ref_count = 1
            block.last_accessed = time.time()
            block.is_prefix = is_prefix
            block.prefix_hash = prefix_hash
            return block
        if len(self._blocks) >= self.max_cache_blocks:
            self._evict()
        block_id = self._next_block_id
        self._next_block_id += 1
        shape = (self.max_batch_size, self.num_heads, self.block_size, self.head_dim)
        k = torch.zeros(shape, device=self.device, dtype=self.dtype)
        v = torch.zeros(shape, device=self.device, dtype=self.dtype)
        block = KVCacheBlock(
            block_id=block_id,
            layer_idx=layer_idx,
            k=k,
            v=v,
            is_prefix=is_prefix,
            prefix_hash=prefix_hash,
        )
        self._blocks[block_id] = block
        return block

    def _evict(self) -> None:
        candidates = [b for b in self._blocks.values() if b.ref_count == 0 and not b.is_prefix]
        if not candidates:
            candidates = [b for b in self._blocks.values() if b.ref_count == 0]
        if not candidates:
            candidates = sorted(self._blocks.values(), key=lambda b: b.last_accessed)
        victim = min(candidates, key=lambda b: b.last_accessed)
        del self._blocks[victim.block_id]
        self._evictions += 1

    def update(self, blocks: list[KVCacheBlock], k: torch.Tensor, v: torch.Tensor, offset: int) -> None:
        for i, block in enumerate(blocks):
            block.last_accessed = time.time()
            pos_in_block = offset + i * self.block_size
            actual_len = min(self.block_size, k.shape[2] - pos_in_block)
            if actual_len > 0:
                block.k[:, :, :actual_len, :] = k[:, :, pos_in_block:pos_in_block + actual_len, :]
                block.v[:, :, :actual_len, :] = v[:, :, pos_in_block:pos_in_block + actual_len, :]

    def release(self, blocks: list[KVCacheBlock]) -> None:
        for block in blocks:
            block.ref_count -= 1
            if block.ref_count <= 0:
                self._free_list.append(block.block_id)

    def metrics(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "blocks_allocated": len(self._blocks),
            "blocks_free": len(self._free_list),
            "hit_ratio": self._hits / total if total > 0 else 0.0,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
        }
