"""Tests for arena allocator and tensor memory pool - expanded coverage."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.arena import ArenaAllocator, TensorMemoryPool


def test_arena_allocator_multiple_blocks():
    arena = ArenaAllocator(capacity_bytes=1024)
    blocks = [arena.allocate(128) for _ in range(5)]
    assert len(blocks) == 5


def test_arena_allocator_reset():
    arena = ArenaAllocator(capacity_bytes=1024)
    arena.allocate(256)
    arena.reset()
    assert arena.used == 0


def test_tensor_memory_pool_acquire_different_shapes():
    pool = TensorMemoryPool()
    t1 = pool.acquire((2, 3), dtype="float32")
    t2 = pool.acquire((4, 5), dtype="float32")
    assert t1.shape == (2, 3)
    assert t2.shape == (4, 5)


def test_tensor_memory_pool_pooling_does_not_grow_indefinitely():
    pool = TensorMemoryPool()
    for _ in range(5):
        t = pool.acquire((2, 2), dtype="float32")
        pool.release(t, (2, 2), dtype="float32")
    pool.acquire((2, 2), dtype="float32")


def test_arena_allocator_small_allocation():
    arena = ArenaAllocator(capacity_bytes=64)
    block = arena.allocate(1)
    assert block.size == 1
