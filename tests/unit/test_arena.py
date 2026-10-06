"""Tests for arena allocator and tensor memory pool."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.arena import ArenaAllocator, TensorMemoryPool


def test_arena_allocator_allocate_and_free():
    arena = ArenaAllocator(capacity_bytes=1024)
    block = arena.allocate(256)
    assert block.size == 256
    arena.free(block)
    assert arena.used == 0


def test_arena_allocator_exhausted_raises():
    arena = ArenaAllocator(capacity_bytes=128)
    arena.allocate(128)
    with pytest.raises(MemoryError):
        arena.allocate(1)


def test_tensor_memory_pool_reuse():
    pool = TensorMemoryPool()
    t1 = pool.acquire((2, 3), dtype="float32")
    pool.release(t1, (2, 3), dtype="float32")
    t2 = pool.acquire((2, 3), dtype="float32")
    assert t1 is t2
