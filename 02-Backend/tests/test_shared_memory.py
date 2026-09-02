"""Tests for shared memory system."""

import pytest
import time
from app.shared_memory import (
    MemoryEntry,
    SharedContext,
    MemoryStore,
    SharedMemoryManager,
)


class TestMemoryStore:
    def test_store_and_get(self):
        store = MemoryStore()
        entry = MemoryEntry(id="m1", content="Test memory", user_id="u1")
        store.store(entry)
        result = store.get("m1")
        assert result is not None
        assert result.content == "Test memory"

    def test_search(self):
        store = MemoryStore()
        store.store(MemoryEntry(id="m1", content="Python programming", user_id="u1"))
        store.store(MemoryEntry(id="m2", content="JavaScript coding", user_id="u1"))
        results = store.search("python", user_id="u1")
        assert len(results) == 1

    def test_get_by_user(self):
        store = MemoryStore()
        store.store(MemoryEntry(id="m1", content="Test", user_id="u1"))
        store.store(MemoryEntry(id="m2", content="Test", user_id="u2"))
        results = store.get_by_user("u1")
        assert len(results) == 1

    def test_delete(self):
        store = MemoryStore()
        store.store(MemoryEntry(id="m1", content="Test", user_id="u1"))
        assert store.delete("m1") is True
        assert store.get("m1") is None

    def test_cleanup_expired(self):
        store = MemoryStore()
        store.store(MemoryEntry(id="m1", content="Test", user_id="u1", expires_at=time.time() - 1))
        store.store(MemoryEntry(id="m2", content="Test", user_id="u1"))
        removed = store.cleanup_expired()
        assert removed == 1


class TestSharedMemoryManager:
    def test_create_memory(self):
        mgr = SharedMemoryManager()
        entry = mgr.create_memory("Test content", "u1", importance=2.0)
        assert entry.id is not None
        assert entry.content == "Test content"

    def test_recall(self):
        mgr = SharedMemoryManager()
        mgr.create_memory("Python is great", "u1")
        results = mgr.recall("python", user_id="u1")
        assert len(results) > 0

    def test_forget(self):
        mgr = SharedMemoryManager()
        entry = mgr.create_memory("Test", "u1")
        assert mgr.forget(entry.id) is True

    def test_set_get_context(self):
        mgr = SharedMemoryManager()
        mgr.set_context("s1", "key1", "value1")
        assert mgr.get_context("s1", "key1") == "value1"

    def test_compress_memories(self):
        mgr = SharedMemoryManager()
        mgr.create_memory("Memory 1", "u1")
        mgr.create_memory("Memory 2", "u1")
        result = mgr.compress_memories("u1")
        assert result["compressed"] is True
        assert result["total_memories"] == 2

    def test_get_stats(self):
        mgr = SharedMemoryManager()
        mgr.create_memory("Test", "u1")
        stats = mgr.get_stats("u1")
        assert stats["total"] == 1
