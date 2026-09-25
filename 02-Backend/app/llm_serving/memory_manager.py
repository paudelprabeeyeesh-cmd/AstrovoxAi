"""GPU memory management and eviction policies."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import torch

logger = logging.getLogger(__name__)


class EvictionPolicy(str, Enum):
    LRU = "lru"
    LFU = "lfu"
    RANDOM = "random"
    SCORE_BASED = "score_based"
    ADAPTIVE = "adaptive"


@dataclass
class MemoryBlock:
    block_id: str
    size_bytes: int
    allocated_at: float
    last_accessed: float
    priority: float = 1.0
    ref_count: int = 1
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}

    def score(self, policy: EvictionPolicy, now: float) -> float:
        age = now - self.allocated_at
        recency = now - self.last_accessed
        if policy == EvictionPolicy.LRU:
            return recency
        if policy == EvictionPolicy.LFU:
            return 1.0 / max(self.ref_count, 1)
        if policy == EvictionPolicy.RANDOM:
            import random
            return random.random()
        if policy == EvictionPolicy.SCORE_BASED:
            return (recency * 0.5) + (age * 0.3) + (1.0 / max(self.priority, 0.1) * 0.2)
        return recency + (1.0 / max(self.ref_count, 1))


class GPUMemoryManager:
    def __init__(
        self,
        device: torch.device,
        max_memory_bytes: int,
        reserved_bytes: int = 256 * 1024 * 1024,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        eviction_threshold: float = 0.85,
        enable_ooms_prevention: bool = True,
    ):
        self.device = device
        self.max_memory = max_memory_bytes
        self.reserved = reserved_bytes
        self.eviction_policy = eviction_policy
        self.eviction_threshold = eviction_threshold
        self.enable_ooms_prevention = enable_ooms_prevention
        self._blocks: dict[str, MemoryBlock] = {}
        self._allocated_bytes = 0
        self._peak_bytes = 0
        self._evictions = 0
        self._oom_count = 0
        self._allocation_count = 0
        self._free_count = 0

    def allocate(self, block_id: str, size_bytes: int, priority: float = 1.0, metadata: Optional[dict[str, Any]] = None) -> bool:
        if self.enable_ooms_prevention and not self._can_allocate(size_bytes):
            self._evict_until_fit(size_bytes)
        if not self._can_allocate(size_bytes):
            self._oom_count += 1
            logger.error("OOM: cannot allocate %d bytes on %s", size_bytes, self.device)
            torch.cuda.empty_cache()
            return False
        block = MemoryBlock(
            block_id=block_id,
            size_bytes=size_bytes,
            allocated_at=time.time(),
            last_accessed=time.time(),
            priority=priority,
            metadata=metadata or {},
        )
        self._blocks[block_id] = block
        self._allocated_bytes += size_bytes
        self._peak_bytes = max(self._peak_bytes, self._allocated_bytes)
        self._allocation_count += 1
        return True

    def free(self, block_id: str) -> None:
        block = self._blocks.pop(block_id, None)
        if block:
            self._allocated_bytes -= block.size_bytes
            self._free_count += 1

    def touch(self, block_id: str) -> None:
        block = self._blocks.get(block_id)
        if block:
            block.last_accessed = time.time()
            block.ref_count += 1

    def release(self, block_id: str) -> None:
        block = self._blocks.get(block_id)
        if block:
            block.ref_count -= 1
            if block.ref_count <= 0:
                self.free(block_id)

    def _can_allocate(self, size_bytes: int) -> bool:
        available = self.max_memory - self.reserved - self._allocated_bytes
        return available >= size_bytes

    def _evict_until_fit(self, size_bytes: int) -> None:
        available = self.max_memory - self.reserved - self._allocated_bytes
        needed = size_bytes - available
        evicted = 0
        candidates = sorted(
            [b for b in self._blocks.values() if b.ref_count <= 1],
            key=lambda b: b.score(self.eviction_policy, time.time()),
        )
        for block in candidates:
            if evicted >= needed:
                break
            self.free(block.block_id)
            evicted += block.size_bytes
            self._evictions += 1

    def maybe_evict(self) -> None:
        utilization = self._allocated_bytes / (self.max_memory - self.reserved)
        if utilization >= self.eviction_threshold:
            self._evict_until_fit(int(self._allocated_bytes * 0.1))

    def metrics(self) -> dict[str, Any]:
        utilization = self._allocated_bytes / max(self.max_memory - self.reserved, 1)
        return {
            "allocated_bytes": self._allocated_bytes,
            "peak_bytes": self._peak_bytes,
            "max_bytes": self.max_memory,
            "reserved_bytes": self.reserved,
            "utilization": utilization,
            "blocks_active": len(self._blocks),
            "allocation_count": self._allocation_count,
            "free_count": self._free_count,
            "evictions": self._evictions,
            "oom_count": self._oom_count,
        }
