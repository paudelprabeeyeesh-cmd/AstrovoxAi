"""Tests for memory allocator - expanded coverage."""

from __future__ import annotations

import pytest

from astrovox.memory import MemoryPool, SizeClassAllocator, align_up, product


def test_size_class_allocator_max_size():
    allocator = SizeClassAllocator(max_size=256, class_step=64)
    block = allocator.allocate(200)
    assert block.size <= 256


def test_align_up_zero():
    assert align_up(0, 64) == 0


def test_align_up_exact_multiple():
    assert align_up(128, 64) == 128


def test_product_single_dimension():
    assert product((7,)) == 7


def test_memory_pool_reuse_after_free():
    pool = MemoryPool(block_size=32, capacity=2)
    b1 = pool.allocate()
    pool.free(b1)
    b2 = pool.allocate()
    assert b2.size == 32
