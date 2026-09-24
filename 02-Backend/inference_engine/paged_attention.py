
import numpy as np
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class KVCachePage:
    page_id: int
    layer_idx: int
    logical_block: int
    data: Optional[np.ndarray] = None
    ref_count: int = 0
    is_dirty: bool = False
    last_access: float = 0.0

    def touch(self, timestamp: float):
        self.last_access = timestamp


class PageTable:
    def __init__(self):
        self.logical_to_physical: Dict[Tuple[int, int], int] = {}
        self.physical_to_logical: Dict[int, Tuple[int, int]] = {}
        self.next_page_id = 0

    def map(self, logical_block: int, layer_idx: int, page_id: int):
        key = (layer_idx, logical_block)
        self.logical_to_physical[key] = page_id
        self.physical_to_logical[page_id] = key

    def unmap(self, logical_block: int, layer_idx: int):
        key = (layer_idx, logical_block)
        page_id = self.logical_to_physical.pop(key, None)
        if page_id is not None:
            self.physical_to_logical.pop(page_id, None)
        return page_id

    def get_page_id(self, logical_block: int, layer_idx: int) -> Optional[int]:
        return self.logical_to_physical.get((layer_idx, logical_block))

    def __len__(self):
        return len(self.logical_to_physical)


class KVCache:
    def __init__(self, num_layers: int, num_heads: int, head_dim: int,
                 page_size: int = 16, max_pages: int = 1024):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.page_size = page_size
        self.max_pages = max_pages
        self.page_table = PageTable()
        self.pages: Dict[int, KVCachePage] = {}
        self.free_list: deque = deque(range(max_pages))
        self._timestamp = 0.0
        self.eviction_policy = "lru"

    def _now(self) -> float:
        self._timestamp += 1.0
        return self._timestamp

    def allocate_page(self, layer_idx: int, logical_block: int = -1) -> Optional[int]:
        if not self.free_list:
            self._evict()
        if not self.free_list:
            return None
        page_id = self.free_list.popleft()
        data = np.zeros((self.page_size, self.num_heads, self.head_dim), dtype=np.float32)
        page = KVCachePage(page_id=page_id, layer_idx=layer_idx,
                           logical_block=logical_block, data=data, ref_count=1)
        page.touch(self._now())
        self.pages[page_id] = page
        if logical_block >= 0:
            self.page_table.map(logical_block, layer_idx, page_id)
        return page_id

    def get_or_allocate(self, logical_block: int, layer_idx: int) -> Optional[int]:
        existing = self.page_table.get_page_id(logical_block, layer_idx)
        if existing is not None and existing in self.pages:
            self.pages[existing].touch(self._now())
            self.pages[existing].ref_count += 1
            return existing
        return self.allocate_page(layer_idx, logical_block)

    def write_kv(self, layer_idx: int, logical_block: int, data: np.ndarray):
        page_id = self.get_or_allocate(logical_block=logical_block, layer_idx=layer_idx)
        if page_id is None:
            raise MemoryError("KV cache full")
        page = self.pages[page_id]
        page.data = data.astype(np.float32).copy()
        page.is_dirty = True
        page.touch(self._now())

    def get_kv(self, layer_idx: int, logical_block: int) -> Optional[np.ndarray]:
        page_id = self.page_table.get_page_id(logical_block, layer_idx)
        if page_id is None or page_id not in self.pages:
            return None
        page = self.pages[page_id]
        page.touch(self._now())
        return page.data

    def release(self, logical_block: int, layer_idx: int):
        page_id = self.page_table.unmap(logical_block, layer_idx)
        if page_id is None or page_id not in self.pages:
            return
        page = self.pages[page_id]
        page.ref_count -= 1
        if page.ref_count <= 0:
            self.free_list.append(page_id)
            del self.pages[page_id]

    def _evict(self):
        if not self.pages:
            return
        candidates = [(p.last_access, pid) for pid, p in self.pages.items()
                      if p.ref_count == 0 and pid not in list(self.free_list)]
        if not candidates:
            return
        candidates.sort()
        _, victim_id = candidates[0]
        victim = self.pages[victim_id]
        if victim.logical_block >= 0:
            self.page_table.unmap(victim.logical_block, victim.layer_idx)
        self.free_list.append(victim_id)
        del self.pages[victim_id]

    def get_memory_usage(self) -> Dict:
        used_pages = sum(1 for p in self.pages.values() if p.ref_count > 0)
        total_bytes = used_pages * self.page_size * self.num_heads * self.head_dim * 2 * 4
        return {
            "num_pages": used_pages,
            "max_pages": self.max_pages,
            "total_bytes": total_bytes,
            "utilization": used_pages / self.max_pages if self.max_pages > 0 else 0.0,
        }

    def cow_copy(self, logical_block: int, layer_idx: int) -> Optional[int]:
        old_page_id = self.page_table.get_page_id(logical_block, layer_idx)
        if old_page_id is None or old_page_id not in self.pages:
            return self.allocate_page(layer_idx, logical_block)
        old_page = self.pages[old_page_id]
        new_page_id = self.allocate_page(layer_idx, logical_block)
        if new_page_id is None:
            return None
        if old_page.data is not None:
            self.pages[new_page_id].data = old_page.data.copy()
        old_page.ref_count -= 1
        self.pages[new_page_id].ref_count = 1
        self.page_table.unmap(logical_block, layer_idx)
        self.page_table.map(logical_block, layer_idx, new_page_id)
        return new_page_id


def paged_attention_forward(q: np.ndarray, cache: KVCache,
                             page_table: PageTable, scale: float = 1.0) -> np.ndarray:
    batch_size, num_heads, seq_len_q, head_dim = q.shape
    out = np.zeros((batch_size, num_heads, seq_len_q, head_dim), dtype=np.float32)
    valid_pages = [(pid, p) for pid, p in cache.pages.items() if p.data is not None and p.ref_count > 0]
    for b in range(batch_size):
        for h in range(num_heads):
            q_bh = q[b, h]
            k_list = []
            v_list = []
            for pid, page in valid_pages:
                k_list.append(page.data[:, h, :])
                v_list.append(page.data[:, h, :])
            if not k_list:
                continue
            k = np.vstack(k_list)
            v = np.vstack(v_list)
            kv_len = k.shape[0]
            scores = q_bh @ k.T * scale
            causal_mask = np.triu(np.ones((seq_len_q, kv_len), dtype=np.float32) * -1e9, k=1)
            scores = scores + causal_mask
            attn_weights = softmax(scores)
            out[b, h] = attn_weights @ v
    return out


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / (np.sum(exp_x, axis=-1, keepdims=True) + 1e-9)
