"""Memory allocator and pooling utilities.

Goal: reduce allocation overhead and peak memory usage by reusing buffers
for tensors with similar sizes and short lifetimes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Block:
    """One reusable memory block."""

    size: int
    address: int = 0


class MemoryPool:
    """Simple bump-allocator style pool for fixed-size blocks."""

    def __init__(self, block_size: int, capacity: int) -> None:
        self.block_size = max(1, block_size)
        self.capacity = max(1, capacity)
        self.used = 0

    def allocate(self) -> Block:
        if self.used >= self.capacity:
            raise MemoryError("pool exhausted")
        block = Block(size=self.block_size, address=self.used * self.block_size)
        self.used += 1
        return block

    def free(self, block: Block) -> None:
        self.used = max(0, self.used - 1)


class SizeClassAllocator:
    """Coalesces allocations into size classes to improve reuse."""

    def __init__(self, max_size: int = 2 ** 20, class_step: int = 64) -> None:
        self.max_size = max(1, max_size)
        self.class_step = max(1, class_step)
        self.pools: dict[int, MemoryPool] = {}

    def _class_for(self, size: int) -> int:
        return min(self.max_size, max(self.class_step, (max(1, size) + self.class_step - 1) // self.class_step * self.class_step))

    def allocate(self, size: int, capacity: int = 1024) -> Block:
        cls = self._class_for(size)
        pool = self.pools.setdefault(cls, MemoryPool(block_size=cls, capacity=capacity))
        return pool.allocate()

    def release(self, block: Block) -> None:
        pool = self.pools.get(block.size)
        if pool is not None:
            pool.free(block)


def align_up(value: int, alignment: int = 64) -> int:
    if alignment <= 0:
        return value
    return (value + alignment - 1) // alignment * alignment


def product(dimensions: Sequence[int]) -> int:
    result = 1
    for dim in dimensions:
        result *= int(dim)
    return result
