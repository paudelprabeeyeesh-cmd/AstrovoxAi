"""Tests for memory allocator and pooling utilities."""

from __future__ import annotations

import pytest

from astrovox.memory import MemoryPool, SizeClassAllocator, align_up, product


def test_memory_pool_allocate_and_free():
    pool = MemoryPool(block_size=64, capacity=4)
    block1 = pool.allocate()
    assert block1.size == 64
    pool.free(block1)
    block2 = pool.allocate()
    assert block2.size == 64


def test_memory_pool_exhausted_raises():
    pool = MemoryPool(block_size=64, capacity=1)
    pool.allocate()
    with pytest.raises(MemoryError):
        pool.allocate()


def test_size_class_allocator_rounds_up():
    allocator = SizeClassAllocator(max_size=1024, class_step=64)
    block = allocator.allocate(100)
    assert block.size % 64 == 0


def test_align_up_returns_multiple_of_alignment():
    assert align_up(10, 8) == 16
    assert align_up(16, 8) == 16
    assert align_up(0, 8) == 0


def test_product_of_dimensions():
    assert product((2, 3, 4)) == 24
    assert product(()) == 1
    assert product((5,)) == 5
