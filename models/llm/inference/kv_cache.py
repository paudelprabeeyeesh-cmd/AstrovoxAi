import hashlib
import logging
import math
from collections import OrderedDict
from typing import Optional

import torch

logger = logging.getLogger(__name__)


class KVCacheBlock:
    def __init__(self, num_layers: int, num_heads: int, block_size: int, head_dim: int, device, dtype):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.block_size = block_size
        self.head_dim = head_dim
        self.key = torch.zeros(num_layers, num_heads, block_size, head_dim, device=device, dtype=dtype)
        self.value = torch.zeros(num_layers, num_heads, block_size, head_dim, device=device, dtype=dtype)
        self.used = 0

    def is_full(self) -> bool:
        return self.used >= self.block_size

    def available(self) -> int:
        return self.block_size - self.used


class PagedKVCache:
    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        block_size: int = 16,
        max_blocks: int = 1024,
        device = None,
        dtype = None,
    ):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.device = device or torch.device("cpu")
        self.dtype = dtype or torch.float32
        self.blocks: list[KVCacheBlock] = [
            KVCacheBlock(num_layers, num_heads, block_size, head_dim, self.device, self.dtype)
            for _ in range(max_blocks)
        ]
        self.free_blocks = list(range(max_blocks))
        self.allocated: list[int] = []
        self.seq_map: dict[str, list[int]] = {}
        self.seq_lengths: dict[str, int] = {}
        self.lru: list[str] = []

    def _allocate_block(self) -> int:
        if not self.free_blocks:
            raise MemoryError("Paged KV cache exhausted")
        block_id = self.free_blocks.pop(0)
        self.allocated.append(block_id)
        return block_id

    def _free_sequence(self, seq_id: str):
        blocks = self.seq_map.pop(seq_id, [])
        for b in blocks:
            if b in self.allocated:
                self.allocated.remove(b)
            self.free_blocks.append(b)
            self.blocks[b].used = 0
        self.seq_lengths.pop(seq_id, None)
        if seq_id in self.lru:
            self.lru.remove(seq_id)

    def reset(self):
        self.free_blocks = list(range(self.max_blocks))
        self.blocks = [
            KVCacheBlock(self.num_layers, self.num_heads, self.block_size, self.head_dim, self.device, self.dtype)
            for _ in range(self.max_blocks)
        ]
        self.allocated.clear()
        self.seq_map.clear()
        self.seq_lengths.clear()
        self.lru.clear()

    def get(self, seq_id: str) -> tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        blocks = self.seq_map.get(seq_id, [])
        if not blocks:
            return None, None
        keys = [self.blocks[b].key[:, :, : self.blocks[b].used, :] for b in blocks]
        values = [self.blocks[b].value[:, :, : self.blocks[b].used, :] for b in blocks]
        return torch.cat(keys, dim=2), torch.cat(values, dim=2)

    def allocate(self, seq_id: str, num_tokens: int):
        self._free_sequence(seq_id)
        num_blocks = max(1, math.ceil(num_tokens / self.block_size))
        if num_blocks > len(self.free_blocks):
            self._evict_lru(num_blocks - len(self.free_blocks))
            if num_blocks > len(self.free_blocks):
                raise MemoryError(f"Need {num_blocks} blocks, only {len(self.free_blocks)} free")
        block_ids = [self._allocate_block() for _ in range(num_blocks)]
        self.seq_map[seq_id] = block_ids
        self.seq_lengths[seq_id] = num_tokens
        self.lru.append(seq_id)

    def _evict_lru(self, needed: int) -> None:
        evicted = 0
        while evicted < needed and self.lru:
            victim = self.lru.pop(0)
            if victim in self.seq_map:
                self._free_sequence(victim)
                evicted += 1

    def update(self, seq_id: str, layer_idx: int, key: torch.Tensor, value: torch.Tensor):
        blocks = self.seq_map.get(seq_id, [])
        if not blocks:
            raise KeyError(f"Sequence {seq_id} not allocated")
        total = self.seq_lengths.get(seq_id, 0)
        offset = total
        block_idx = offset // self.block_size
        intra_offset = offset % self.block_size
        if block_idx >= len(blocks):
            raise IndexError(f"Block index {block_idx} out of range for sequence {seq_id}")
        k_block = self.blocks[blocks[block_idx]].key
        v_block = self.blocks[blocks[block_idx]].value
        write_len = min(key.size(2), self.block_size - intra_offset)
        k_block[layer_idx, :, intra_offset : intra_offset + write_len, :] = key[:, :, :write_len, :]
        v_block[layer_idx, :, intra_offset : intra_offset + write_len, :] = value[:, :, :write_len, :]
        self.blocks[blocks[block_idx]].used = max(self.blocks[blocks[block_idx]].used, intra_offset + write_len)
        self.seq_lengths[seq_id] = total + write_len

    def get_length(self, seq_id: str) -> int:
        return self.seq_lengths.get(seq_id, 0)

    def evict(self, seq_id: str) -> None:
        self._free_sequence(seq_id)


class PrefixCache:
    def __init__(self, max_size: int = 512):
        self.store: dict[str, tuple[list[int], float]] = OrderedDict()
        self.max_size = max_size

    def _key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> Optional[tuple[list[int], float]]:
        key = self._key(prompt)
        entry = self.store.get(key)
        if entry is not None:
            self.store.move_to_end(key)
            return entry
        return None

    def put(self, prompt: str, token_ids: list[int], timestamp: float = 0.0) -> None:
        key = self._key(prompt)
        self.store[key] = (token_ids, timestamp)
        self.store.move_to_end(key)
        if len(self.store) > self.max_size:
            self.store.popitem(last=False)

    def clear(self):
        self.store.clear()
