"""PagedAttention KV cache for ASTROVOX_AI inference core."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class KVBlock:
    block_id: int
    layer_idx: int
    k: torch.Tensor
    v: torch.Tensor
    ref_count: int = 1
    is_prefix: bool = False
    prefix_hash: Optional[str] = None
    last_accessed: float = 0.0

    def __post_init__(self) -> None:
        if self.last_accessed == 0.0:
            self.last_accessed = time.time()


class PagedKVCache:
    def __init__(self, num_layers: int, num_heads: int, head_dim: int, max_seq_len: int, block_size: int, max_blocks: int, device: torch.device, dtype: torch.dtype = torch.float16):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.device = device
        self.dtype = dtype
        self._block_managers: List[Dict[int, KVBlock]] = [{} for _ in range(num_layers)]
        self._free_lists: List[List[int]] = [[] for _ in range(num_layers)]
        self._next_ids: List[int] = [0 for _ in range(num_layers)]
        self._block_tables: Dict[int, List[int]] = {}
        self._prefix_blocks: Dict[str, List[KVBlock]] = {}
        self._seq_lens: Dict[int, int] = {}

    def _allocate_block(self, layer_idx: int, is_prefix: bool = False, prefix_hash: Optional[str] = None) -> KVBlock:
        free = self._free_lists[layer_idx]
        if free:
            block_id = free.pop()
            block = self._block_managers[layer_idx][block_id]
            block.ref_count = 1
            block.is_prefix = is_prefix
            block.prefix_hash = prefix_hash
            block.last_accessed = time.time()
            return block
        if sum(len(m) for m in self._block_managers) >= self.max_blocks * self.num_layers:
            self._evict(layer_idx)
        block_id = self._next_ids[layer_idx]
        self._next_ids[layer_idx] += 1
        shape = (self.num_heads, self.block_size, self.head_dim)
        k = torch.zeros(shape, device=self.device, dtype=self.dtype)
        v = torch.zeros(shape, device=self.device, dtype=self.dtype)
        block = KVBlock(block_id=block_id, layer_idx=layer_idx, k=k, v=v, is_prefix=is_prefix, prefix_hash=prefix_hash)
        self._block_managers[layer_idx][block_id] = block
        return block

    def _evict(self, layer_idx: int) -> None:
        candidates = [b for b in self._block_managers[layer_idx].values() if b.ref_count == 0 and not b.is_prefix]
        if not candidates:
            candidates = [b for b in self._block_managers[layer_idx].values() if b.ref_count == 0]
        if not candidates:
            candidates = sorted(self._block_managers[layer_idx].values(), key=lambda b: b.last_accessed)
        if candidates:
            victim = min(candidates, key=lambda b: b.last_accessed)
            self._block_managers[layer_idx].pop(victim.block_id, None)
            logger.debug("Evicted block %d from layer %d", victim.block_id, layer_idx)

    def reserve(self, seq_id: int, num_blocks: int, layer_idx: int) -> List[KVBlock]:
        blocks = []
        for _ in range(num_blocks):
            blocks.append(self._allocate_block(layer_idx))
        return blocks

    def assign_prefix(self, prefix_hash: str, blocks: List[KVBlock]) -> None:
        for block in blocks:
            block.is_prefix = True
            block.prefix_hash = prefix_hash
        self._prefix_blocks[prefix_hash] = blocks

    def get_prefix(self, prefix_hash: str, layer_idx: int) -> Optional[List[KVBlock]]:
        blocks = self._prefix_blocks.get(prefix_hash)
        if blocks is None:
            return None
        for b in blocks:
            b.ref_count += 1
        return blocks

    def update(self, seq_id: int, layer_idx: int, k: torch.Tensor, v: torch.Tensor, offset: int) -> None:
        table = self._block_tables.setdefault(seq_id, [])
        if not table:
            seq_len = self._seq_lens.get(seq_id, k.shape[2])
            num_blocks = (seq_len + self.block_size - 1) // self.block_size
            for _ in range(num_blocks):
                table.append(self._allocate_block(layer_idx).block_id)
        for i, block_id in enumerate(table):
            block = self._block_managers[layer_idx].get(block_id)
            if block is None:
                continue
            start = i * self.block_size
            end = min(start + self.block_size, k.shape[2])
            actual_len = end - start
            if actual_len > 0:
                src_start = max(0, start - offset)
                src_end = min(k.shape[2], end - offset)
                if src_end > src_start:
                    block.k[:, :actual_len, :] = k[:, :, src_start:src_end, :]
                    block.v[:, :actual_len, :] = v[:, :, src_start:src_end, :]
                block.last_accessed = time.time()

    def release(self, seq_id: int) -> None:
        table = self._block_tables.pop(seq_id, [])
        for block_id in table:
            for layer_idx in range(self.num_layers):
                block = self._block_managers[layer_idx].get(block_id)
                if block:
                    block.ref_count -= 1
                    if block.ref_count <= 0:
                        self._free_lists[layer_idx].append(block_id)

    def metrics(self) -> Dict[str, Any]:
        return {
            "sequences": len(self._block_tables),
            "prefixes": len(self._prefix_blocks),
            "total_blocks": sum(len(m) for m in self._block_managers),
        }


class PagedAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, block_size: int = 16, num_kv_heads: Optional[int] = None, dropout: float = 0.0, max_seq_len: int = 4096, max_blocks: int = 4096, device: str = "cuda"):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads if num_kv_heads is not None else num_heads
        self.head_dim = hidden_size // num_heads
        self.block_size = block_size
        self.num_key_value_groups = num_heads // self.num_kv_heads
        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim)
        self.k_proj = nn.Linear(hidden_size, self.num_kv_heads * self.head_dim)
        self.v_proj = nn.Linear(hidden_size, self.num_kv_heads * self.head_dim)
        self.out_proj = nn.Linear(num_heads * self.head_dim, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.kv_cache = PagedKVCache(
            num_layers=1,
            num_heads=self.num_kv_heads,
            head_dim=self.head_dim,
            max_seq_len=max_seq_len,
            block_size=block_size,
            max_blocks=max_blocks,
            device=torch.device(device),
        )

    def forward(self, x: torch.Tensor, seq_id: Optional[int] = None, layer_idx: int = 0, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)

        if seq_id is not None:
            self.kv_cache.update(seq_id, layer_idx, k, v, offset=0)

        k_cached, v_cached = self._get_cached_kv(seq_id, layer_idx, T)
        if k_cached is not None:
            k = torch.cat([k_cached, k], dim=2)
            v = torch.cat([v_cached, v], dim=2)

        if self.num_key_value_groups > 1:
            k = k.repeat_interleave(self.num_key_value_groups, dim=1)
            v = v.repeat_interleave(self.num_key_value_groups, dim=1)

        scale = self.head_dim ** -0.5
        attn = (q @ k.transpose(-2, -1)) * scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float("-inf"))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)

    def _get_cached_kv(self, seq_id: Optional[int], layer_idx: int, current_len: int) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        if seq_id is None:
            return None, None
        table = self.kv_cache._block_tables.get(seq_id)
        if not table:
            return None, None
        manager = self.kv_cache._block_managers[layer_idx]
        k_blocks, v_blocks = [], []
        for block_id in table:
            block = manager.get(block_id)
            if block is not None:
                k_blocks.append(block.k)
                v_blocks.append(block.v)
        if not k_blocks:
            return None, None
        k = torch.cat(k_blocks, dim=1)
        v = torch.cat(v_blocks, dim=1)
        return k[:, :, :current_len, :], v[:, :, :current_len, :]
