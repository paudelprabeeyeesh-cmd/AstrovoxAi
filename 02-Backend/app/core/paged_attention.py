"""
PagedAttention implementation in pure Python/NumPy.

Simulates the CUDA logic of vLLM-style PagedAttention:
- Fixed-size KV cache pages
- PageTable for logical-to-physical mapping
- Block allocator with LRU eviction
- Attention computation through page table
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class KVCachePage:
    page_id: int
    token_start: int
    token_end: int
    data: Optional[np.ndarray] = None


@dataclass
class PageTableEntry:
    logical_block: int
    physical_page_id: int
    ref_count: int = 1
    dirty: bool = False


class KVCache:
    """Fixed-size KV cache split into pages."""

    def __init__(self, num_layers: int, num_heads: int, head_dim: int, page_size: int = 16, max_pages: int = 1024):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.page_size = page_size
        self.max_pages = max_pages
        self.pages: Dict[int, Dict[int, np.ndarray]] = {}
        self.page_table: Dict[int, PageTableEntry] = {}
        self.lru: OrderedDict = OrderedDict()
        self.next_page_id = 0

    def allocate_page(self, layer_idx: int) -> int:
        page_id = self.next_page_id
        self.next_page_id += 1
        shape = (self.page_size, self.num_heads, self.head_dim)
        self.pages.setdefault(layer_idx, {})[page_id] = np.zeros(shape, dtype=np.float16)
        self.lru[page_id] = layer_idx
        return page_id

    def get_or_allocate(self, logical_block: int, layer_idx: int) -> int:
        if logical_block in self.page_table:
            entry = self.page_table[logical_block]
            self.lru.pop(entry.physical_page_id, None)
            self.lru[entry.physical_page_id] = layer_idx
            return entry.physical_page_id
        if len(self.page_table) >= self.max_pages:
            self._evict()
        page_id = self.allocate_page(layer_idx)
        self.page_table[logical_block] = PageTableEntry(logical_block=logical_block, physical_page_id=page_id)
        return page_id

    def _evict(self):
        if not self.lru:
            return
        oldest_page_id, _ = self.lru.popitem(last=False)
        entry_to_remove = None
        for entry in self.page_table.values():
            if entry.physical_page_id == oldest_page_id:
                entry_to_remove = entry.logical_block
                break
        if entry_to_remove is not None:
            del self.page_table[entry_to_remove]
            for layer_pages in self.pages.values():
                layer_pages.pop(oldest_page_id, None)

    def get_kv(self, layer_idx: int, logical_block: int) -> Optional[np.ndarray]:
        entry = self.page_table.get(logical_block)
        if entry is None:
            return None
        return self.pages.get(layer_idx, {}).get(entry.physical_page_id)

    def write_kv(self, layer_idx: int, logical_block: int, data: np.ndarray):
        page_id = self.get_or_allocate(logical_block, layer_idx)
        self.pages[layer_idx][page_id] = data.astype(np.float16)
        self.page_table[logical_block].dirty = True

    def get_memory_usage(self) -> dict:
        total_pages = sum(len(layer_pages) for layer_pages in self.pages.values())
        total_bytes = total_pages * self.page_size * self.num_heads * self.head_dim * 2
        return {
            "num_pages": total_pages,
            "max_pages": self.max_pages,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
        }


def paged_attention_forward(q: np.ndarray, kv_cache: KVCache, page_table: Dict[int, PageTableEntry], scale: float = 1.0) -> np.ndarray:
    """Compute attention by iterating through the page table."""
    batch_size, num_heads, seq_len, head_dim = q.shape
    out = np.zeros_like(q)
    for b in range(batch_size):
        for h in range(num_heads):
            for s in range(seq_len):
                scores = []
                keys = []
                values = []
                for logical_block, entry in page_table.items():
                    kv = kv_cache.get_kv(0, logical_block)
                    if kv is None:
                        continue
                    block_len = kv.shape[0]
                    for t in range(block_len):
                        global_t = logical_block * kv_cache.page_size + t
                        if global_t > s:
                            break
                        k_vec = kv[t, h, :]
                        v_vec = kv[t, h, :]
                        score = np.dot(q[b, h, s, :], k_vec) * scale
                        scores.append(score)
                        keys.append(global_t)
                        values.append(v_vec)
                if not scores:
                    continue
                scores = np.array(scores)
                max_score = np.max(scores)
                exp_scores = np.exp(scores - max_score)
                sum_exp = np.sum(exp_scores)
                attn_weights = exp_scores / sum_exp
                out[b, h, s, :] = sum(attn_weights[i] * values[i] for i in range(len(values)))
    return out


@dataclass
class ContinuousBatch:
    batch_id: str
    max_batch_size: int = 32
    active_requests: List[dict] = field(default_factory=list)
    queued_requests: List[dict] = field(default_factory=list)
    preempted_requests: List[dict] = field(default_factory=list)

    def add_request(self, request: dict) -> bool:
        if len(self.active_requests) < self.max_batch_size:
            self.active_requests.append(request)
            return True
        self.queued_requests.append(request)
        return False

    def on_token_complete(self, request_id: str) -> Optional[str]:
        for req in self.active_requests:
            if req.get("id") == request_id:
                self.active_requests.remove(req)
                if self.queued_requests:
                    next_req = self.queued_requests.pop(0)
                    self.active_requests.append(next_req)
                    return next_req.get("id")
                if self.preempted_requests:
                    next_req = self.preempted_requests.pop(0)
                    self.active_requests.append(next_req)
                    return next_req.get("id")
                return None
        return None

    def preempt_lowest_priority(self) -> Optional[str]:
        if not self.active_requests:
            return None
        req = min(self.active_requests, key=lambda r: r.get("priority", 0))
        self.active_requests.remove(req)
        self.preempted_requests.append(req)
        return req.get("id")

    def get_utilization(self) -> float:
        return round(len(self.active_requests) / self.max_batch_size * 100, 1)


class Scheduler:
    """Continuous batching scheduler with preemption."""

    def __init__(self, max_batch_size: int = 32, max_preempted: int = 8):
        self.batches: Dict[str, ContinuousBatch] = {}
        self.max_batch_size = max_batch_size
        self.max_preempted = max_preempted

    def submit(self, request: dict) -> str:
        import uuid
        batch_id = request.get("batch_id", "default")
        if batch_id not in self.batches:
            self.batches[batch_id] = ContinuousBatch(batch_id=batch_id, max_batch_size=self.max_batch_size)
        batch = self.batches[batch_id]
        if not batch.add_request(request):
            if len(batch.preempted_requests) < self.max_preempted:
                batch.preempt_lowest_priority()
                batch.add_request(request)
        return batch_id

    def get_stats(self) -> dict:
        total_active = sum(len(b.active_requests) for b in self.batches.values())
        total_queued = sum(len(b.queued_requests) for b in self.batches.values())
        total_preempted = sum(len(b.preempted_requests) for b in self.batches.values())
        return {
            "num_batches": len(self.batches),
            "total_active": total_active,
            "total_queued": total_queued,
            "total_preempted": total_preempted,
            "utilization": round(total_active / (self.max_batch_size * max(len(self.batches), 1)) * 100, 1),
        }
