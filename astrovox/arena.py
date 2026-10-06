"""Arena allocator and tensor memory pool.

Arena allocators hand out fixed-size blocks and recycle them in bulk.
TensorMemoryPool wraps that API with tensor-friendly helpers so the runtime
can reuse buffers without exposing allocation details to model code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ArenaBlock:
    offset: int
    size: int


class ArenaAllocator:
    """Bump-allocator style arena for fixed-size blocks."""

    def __init__(self, capacity_bytes: int) -> None:
        self.capacity = max(1, capacity_bytes)
        self.used = 0
        self._blocks: list[ArenaBlock] = []

    def allocate(self, size: int) -> ArenaBlock:
        size = max(1, size)
        if self.used + size > self.capacity:
            raise MemoryError("arena exhausted")
        block = ArenaBlock(offset=self.used, size=size)
        self.used += size
        self._blocks.append(block)
        return block

    def free(self, block: ArenaBlock) -> None:
        if block in self._blocks:
            self._blocks.remove(block)
            self.used = max(0, self.used - block.size)

    def reset(self) -> None:
        self._blocks.clear()
        self.used = 0


class TensorMemoryPool:
    """Reuses tensors by shape to reduce allocation overhead."""

    def __init__(self) -> None:
        self._pools: Dict[tuple, list] = {}

    def _key(self, shape: tuple[int, ...], dtype: str) -> tuple:
        return (shape, dtype)

    def acquire(self, shape: tuple[int, ...], dtype: str = "float32"):
        key = self._key(shape, dtype)
        pool = self._pools.setdefault(key, [])
        if pool:
            return pool.pop()
        import numpy as np
        return np.zeros(shape, dtype=dtype)

    def release(self, tensor, shape: tuple[int, ...], dtype: str = "float32") -> None:
        key = self._key(shape, dtype)
        pool = self._pools.setdefault(key, [])
        if len(pool) < 32:
            pool.append(tensor)
