from __future__ import annotations

from hardware_abstraction.task_172_memory_pool_allocator import Block, MemoryPoolAllocator


class TestBlock:
    def test_end(self):
        block = Block(pointer=0, size=16)
        assert block.end == 16

    def test_default_free(self):
        block = Block(pointer=4, size=8)
        assert block.free is False


class TestMemoryPoolAllocator:
    def test_allocate_returns_id(self):
        allocator = MemoryPoolAllocator(total_size=64)
        block_id = allocator.allocate(16)
        assert block_id is not None
        assert block_id.startswith("block-")

    def test_allocate_failure(self):
        allocator = MemoryPoolAllocator(total_size=8)
        assert allocator.allocate(16) is None

    def test_allocate_zero(self):
        allocator = MemoryPoolAllocator(total_size=16)
        assert allocator.allocate(0) is None

    def test_free_returns_true(self):
        allocator = MemoryPoolAllocator(total_size=32)
        block_id = allocator.allocate(8)
        assert allocator.free(block_id) is True

    def test_free_returns_false(self):
        allocator = MemoryPoolAllocator(total_size=32)
        assert allocator.free("missing") is False

    def test_used_and_free_size(self):
        allocator = MemoryPoolAllocator(total_size=64)
        allocator.allocate(16)
        assert allocator.used_size() == 16
        assert allocator.free_size() == 48

    def test_fragmentation(self):
        allocator = MemoryPoolAllocator(total_size=64)
        allocator.allocate(16)
        allocator.allocate(16)
        assert allocator.free_size() == 32

    def test_status_keys(self):
        allocator = MemoryPoolAllocator(total_size=64)
        status = allocator.status()
        assert status["total_size"] == 64
        assert status["used_size"] == 0
        assert status["free_size"] == 64
        assert "fragmentation" in status
        assert "block_count" in status

    def test_coalesce_adjacent_free_blocks(self):
        allocator = MemoryPoolAllocator(total_size=64)
        allocator.allocate(8)
        allocator.allocate(8)
        allocator.free(allocator.allocate(8))
        allocator.free(allocator.allocate(8))
        assert len(allocator.get_free_blocks()) == 1
        assert allocator.free_size() == 48

    def test_coalesce_preserves_used_blocks(self):
        allocator = MemoryPoolAllocator(total_size=64)
        id1 = allocator.allocate(8)
        id2 = allocator.allocate(8)
        allocator.free(id1)
        allocator.free(id2)
        assert len(allocator.get_used_blocks()) == 0
        assert len(allocator.get_free_blocks()) == 1
        assert allocator.free_size() == 64
