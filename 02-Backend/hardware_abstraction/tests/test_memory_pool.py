from __future__ import annotations

from hardware_abstraction.memory_pool import Block, MemoryPool


class TestBlock:
    def test_end(self):
        block = Block(pointer=0, size=16)
        assert block.end == 16

    def test_default_free(self):
        block = Block(pointer=4, size=8)
        assert block.free is False


class TestMemoryPool:
    def test_allocate_returns_id(self):
        pool = MemoryPool(total_size=64)
        block_id = pool.allocate(16)
        assert block_id is not None
        assert block_id.startswith("block-")

    def test_allocate_failure(self):
        pool = MemoryPool(total_size=8)
        assert pool.allocate(16) is None

    def test_allocate_zero(self):
        pool = MemoryPool(total_size=16)
        assert pool.allocate(0) is None

    def test_free_returns_true(self):
        pool = MemoryPool(total_size=32)
        block_id = pool.allocate(8)
        assert pool.free(block_id) is True

    def test_free_returns_false(self):
        pool = MemoryPool(total_size=32)
        assert pool.free("missing") is False

    def test_used_and_free_size(self):
        pool = MemoryPool(total_size=64)
        pool.allocate(16)
        assert pool.used_size() == 16
        assert pool.free_size() == 48

    def test_fragmentation(self):
        pool = MemoryPool(total_size=64)
        pool.allocate(16)
        pool.allocate(16)
        assert pool.free_size() == 32

    def test_status_keys(self):
        pool = MemoryPool(total_size=64)
        status = pool.status()
        assert status["total_size"] == 64
        assert status["used_size"] == 0
        assert status["free_size"] == 64
        assert "fragmentation" in status
        assert "block_count" in status

    def test_coalesce_adjacent_free_blocks(self):
        pool = MemoryPool(total_size=64)
        pool.allocate(8)
        pool.allocate(8)
        pool.free(pool.allocate(8))
        pool.free(pool.allocate(8))
        assert len(pool.get_free_blocks()) == 1
        assert pool.free_size() == 48

    def test_coalesce_preserves_used_blocks(self):
        pool = MemoryPool(total_size=64)
        id1 = pool.allocate(8)
        id2 = pool.allocate(8)
        pool.free(id1)
        pool.free(id2)
        assert len(pool.get_used_blocks()) == 0
        assert len(pool.get_free_blocks()) == 1
        assert pool.free_size() == 64

    def test_non_adjacent_free_blocks_do_not_merge(self):
        pool = MemoryPool(total_size=64)
        id1 = pool.allocate(8)
        pool.allocate(8)
        id3 = pool.allocate(8)
        pool.free(id1)
        pool.free(id3)
        assert len(pool.get_free_blocks()) == 2
