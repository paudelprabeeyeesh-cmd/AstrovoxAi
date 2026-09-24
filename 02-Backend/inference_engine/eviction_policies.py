
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class EvictionPolicy(Enum):
    LRU = "lru"
    LFU = "lfu"
    PRIORITY = "priority"
    COMPLETION_DISTANCE = "completion_distance"


@dataclass
class CacheBlock:
    block_id: int
    logical_block: int
    layer_idx: int
    data: Optional[np.ndarray] = None
    ref_count: int = 0
    last_access: float = 0.0
    access_count: int = 0
    priority: float = 0.0
    completion_distance: int = 0
    is_dirty: bool = False

    def touch(self, timestamp: float):
        self.last_access = timestamp
        self.access_count += 1


class EvictionPolicyManager:
    def __init__(self, policy: EvictionPolicy = EvictionPolicy.LRU):
        self.policy = policy
        self._timestamp = 0.0

    def _now(self) -> float:
        self._timestamp += 1.0
        return self._timestamp

    def select_victim(self, blocks: Dict[int, "CacheBlock"], max_ref_count: int = 0) -> Optional[int]:
        candidates = [(bid, b) for bid, b in blocks.items() if b.ref_count <= max_ref_count]
        if not candidates:
            return None
        if self.policy == EvictionPolicy.LRU:
            return min(candidates, key=lambda x: x[1].last_access)[0]
        elif self.policy == EvictionPolicy.LFU:
            return min(candidates, key=lambda x: x[1].access_count)[0]
        elif self.policy == EvictionPolicy.PRIORITY:
            return min(candidates, key=lambda x: x[1].priority)[0]
        elif self.policy == EvictionPolicy.COMPLETION_DISTANCE:
            return max(candidates, key=lambda x: x[1].completion_distance)[0]
        return candidates[0][0]

    def update_completion_distance(self, block: "CacheBlock", remaining_tokens: int):
        block.completion_distance = remaining_tokens

    def update_priority(self, block: "CacheBlock", priority: float):
        block.priority = priority


class KVCacheWithEviction:
    def __init__(self, num_layers: int, num_heads: int, head_dim: int,
                 page_size: int = 16, max_pages: int = 1024,
                 policy: EvictionPolicy = EvictionPolicy.LRU):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.page_size = page_size
        self.max_pages = max_pages
        self.policy_manager = EvictionPolicyManager(policy)
        self.blocks: Dict[int, CacheBlock] = {}
        self.free_list: List[int] = list(range(max_pages))
        self.next_block_id = 0
        self.page_table: Dict[Tuple[int, int], int] = {}
        self._timestamp = 0.0

    def _now(self) -> float:
        self._timestamp += 1.0
        return self._timestamp

    def allocate(self, logical_block: int, layer_idx: int, priority: float = 0.0) -> Optional[int]:
        if not self.free_list:
            victim_id = self.policy_manager.select_victim(self.blocks)
            if victim_id is not None:
                self._evict(victim_id)
        if not self.free_list:
            return None
        block_id = self.free_list.pop()
        block = CacheBlock(block_id=block_id, logical_block=logical_block,
                           layer_idx=layer_idx, priority=priority)
        block.touch(self._now())
        block.ref_count = 1
        self.blocks[block_id] = block
        self.page_table[(layer_idx, logical_block)] = block_id
        return block_id

    def access(self, logical_block: int, layer_idx: int) -> Optional[int]:
        block_id = self.page_table.get((layer_idx, logical_block))
        if block_id is not None and block_id in self.blocks:
            block = self.blocks[block_id]
            block.touch(self._now())
            block.ref_count += 1
            return block_id
        return None

    def release(self, logical_block: int, layer_idx: int):
        block_id = self.page_table.get((layer_idx, logical_block))
        if block_id is None or block_id not in self.blocks:
            return
        block = self.blocks[block_id]
        block.ref_count -= 1
        if block.ref_count <= 0:
            self._evict(block_id)

    def _evict(self, block_id: int):
        block = self.blocks.get(block_id)
        if block is None:
            return
        self.page_table.pop((block.layer_idx, block.logical_block), None)
        del self.blocks[block_id]
        self.free_list.append(block_id)

    def get_memory_stats(self) -> Dict:
        used = sum(1 for b in self.blocks.values() if b.ref_count > 0)
        return {
            "used_pages": used,
            "free_pages": len(self.free_list),
            "total_pages": self.max_pages,
            "utilization": used / self.max_pages if self.max_pages > 0 else 0.0,
        }
