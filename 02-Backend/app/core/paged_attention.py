"""
Advanced inference engine with paged attention, continuous batching, and prefix caching.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import torch

logger = logging.getLogger(__name__)


@dataclass
class KVCachePage:
    page_id: int
    layer_idx: int
    k: torch.Tensor
    v: torch.Tensor
    ref_count: int = 1
    last_accessed: float = field(default_factory=time.time)
    is_prefix: bool = False
    prefix_hash: Optional[str] = None


@dataclass
class PageTableEntry:
    logical_block: int
    physical_page_id: int
    layer_idx: int
    seq_id: int


class KVCache:
    def __init__(self, num_layers: int, num_heads: int, head_dim: int, page_size: int = 16, max_pages: int = 4096, device: str = "cpu"):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.page_size = page_size
        self.max_pages = max_pages
        self.device = device
        self.pages: List[KVCachePage] = []
        self.page_table: Dict[int, PageTableEntry] = {}
        self._logical_to_physical: Dict[Tuple[int, int, int], int] = {}
        self._next_page_id = 0
        self._evictions = 0

    def allocate_page(self, layer_idx: int) -> int:
        if len(self.pages) >= self.max_pages:
            self._evict()
        page_id = self._next_page_id
        self._next_page_id += 1
        shape = (self.page_size, self.num_heads, self.head_dim)
        k = torch.zeros(shape, device=self.device, dtype=torch.float16)
        v = torch.zeros(shape, device=self.device, dtype=torch.float16)
        page = KVCachePage(page_id=page_id, layer_idx=layer_idx, k=k, v=v)
        self.pages.append(page)
        return page_id

    def get_or_allocate(self, logical_block: int, layer_idx: int, seq_id: int = 0) -> int:
        key = (seq_id, logical_block, layer_idx)
        if key in self._logical_to_physical:
            page_id = self._logical_to_physical[key]
            page = self.pages[page_id]
            page.ref_count += 1
            page.last_accessed = time.time()
            return page_id
        page_id = self.allocate_page(layer_idx)
        self._logical_to_physical[key] = page_id
        self.page_table[logical_block] = PageTableEntry(
            logical_block=logical_block,
            physical_page_id=page_id,
            layer_idx=layer_idx,
            seq_id=seq_id,
        )
        return page_id

    def write_kv(self, layer_idx: int, logical_block: int, data: Any) -> None:
        page_id = self.get_or_allocate(logical_block, layer_idx)
        page = self.pages[page_id]
        if not isinstance(data, torch.Tensor):
            data = torch.tensor(data, device=self.device, dtype=torch.float16)
        actual_len = min(self.page_size, data.shape[0])
        page.k[:actual_len, :, :] = data[:actual_len, :, :] if data.ndim == 3 else data[:actual_len, :]
        page.v[:actual_len, :, :] = data[:actual_len, :, :] if data.ndim == 3 else data[:actual_len, :]
        page.last_accessed = time.time()

    def get_kv(self, layer_idx: int, logical_block: int) -> Optional[torch.Tensor]:
        key = (0, logical_block, layer_idx)
        page_id = self._logical_to_physical.get(key)
        if page_id is None:
            return None
        page = self.pages[page_id]
        return page.k

    def _evict(self) -> None:
        candidates = [p for p in self.pages if p.ref_count <= 1 and not p.is_prefix]
        if not candidates:
            candidates = self.pages
        if candidates:
            victim = min(candidates, key=lambda p: p.last_accessed)
            self.pages.remove(victim)
            self._evictions += 1
            for key, pid in list(self._logical_to_physical.items()):
                if pid == victim.page_id:
                    del self._logical_to_physical[key]
            for logical_block, entry in list(self.page_table.items()):
                if entry.physical_page_id == victim.page_id:
                    del self.page_table[logical_block]

    def get_memory_usage(self) -> Dict[str, Any]:
        total_bytes = sum(p.k.numel() * p.k.element_size() + p.v.numel() * p.v.element_size() for p in self.pages)
        return {
            "num_pages": len(self.pages),
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "page_table_size": len(self.page_table),
            "evictions": self._evictions,
        }


class PagedAttentionKVCache:
    def __init__(self, num_blocks: int = 1000, block_size: int = 16, num_heads: int = 12, head_dim: int = 64, max_seq_len: int = 4096, device: str = "cuda"):
        self.num_blocks = num_blocks
        self.block_size = block_size
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.device = device
        self.k_cache = torch.zeros(num_blocks, num_heads, block_size, head_dim, device=device)
        self.v_cache = torch.zeros(num_blocks, num_heads, block_size, head_dim, device=device)
        self.block_table: Dict[int, List[int]] = {}

    def assign(self, seq_id: int, num_blocks: int) -> None:
        block_ids = list(range(len(self.block_table) * self.block_size, len(self.block_table) * self.block_size + num_blocks))
        self.block_table[seq_id] = block_ids

    def get_kv(self, seq_id: int) -> Tuple[torch.Tensor, torch.Tensor]:
        block_ids = self.block_table.get(seq_id, [])
        k_blocks = [self.k_cache[b] for b in block_ids]
        v_blocks = [self.v_cache[b] for b in block_ids]
        if not k_blocks:
            return torch.empty(0), torch.empty(0)
        return torch.cat(k_blocks, dim=1), torch.cat(v_blocks, dim=1)

    def update(self, seq_id: int, k: torch.Tensor, v: torch.Tensor, slot_offset: int) -> None:
        block_ids = self.block_table.get(seq_id, [])
        if not block_ids:
            return
        for i, block_id in enumerate(block_ids):
            start = i * self.block_size
            end = min(start + self.block_size, k.shape[2])
            self.k_cache[block_id, :, start - slot_offset:end - slot_offset, :] = k[:, :, start:end, :]
            self.v_cache[block_id, :, start - slot_offset:end - slot_offset, :] = v[:, :, start:end, :]


def paged_attention_forward(q: Any, kv_cache: KVCache, page_table: Dict[int, PageTableEntry], scale: float = 1.0) -> torch.Tensor:
    if not isinstance(q, torch.Tensor):
        q = torch.tensor(q, dtype=torch.float32)
    batch_size, num_heads, seq_len, head_dim = q.shape
    k_blocks = []
    v_blocks = []
    for entry in page_table.values():
        page = kv_cache.pages[entry.physical_page_id]
        k_blocks.append(page.k.transpose(0, 1).to(q.dtype))
        v_blocks.append(page.v.transpose(0, 1).to(q.dtype))
    if not k_blocks:
        k = torch.zeros(batch_size, num_heads, 0, head_dim, device=q.device, dtype=q.dtype)
        v = torch.zeros(batch_size, num_heads, 0, head_dim, device=q.device, dtype=q.dtype)
    else:
        k = torch.cat(k_blocks, dim=2).unsqueeze(0).repeat(batch_size, 1, 1, 1)
        v = torch.cat(v_blocks, dim=2).unsqueeze(0).repeat(batch_size, 1, 1, 1)
    attn = torch.matmul(q, k.transpose(-2, -1)) * scale
    attn = attn.softmax(dim=-1)
    out = torch.matmul(attn, v)
    return out
