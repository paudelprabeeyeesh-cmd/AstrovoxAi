from __future__ import annotations

import math
import pytest
import numpy as np
from datetime import datetime, timedelta

from memory_persistence.memory_retrieval import Memory, MemoryRetrieval


def make_memory(memory_id, content, embedding=None, importance=0.5, created_at=None, access_count=0, category="general"):
    return Memory(
        memory_id=memory_id,
        content=content,
        embedding=embedding,
        importance=importance,
        created_at=created_at or datetime.utcnow(),
        access_count=access_count,
        category=category,
    )


@pytest.fixture
def retrieval():
    return MemoryRetrieval()


def test_add_memory(retrieval):
    m = make_memory("m1", "fact1")
    assert retrieval.add_memory(m) == "m1"
    assert "m1" in retrieval._memories


def test_retrieve_top_k(retrieval):
    e = np.array([1.0, 0.0])
    m1 = make_memory("m1", "fact1", embedding=e, importance=1.0)
    m2 = make_memory("m2", "fact2", embedding=e, importance=0.5)
    retrieval.add_memories([m1, m2])
    results = retrieval.retrieve(query_embedding=e, top_k=1)
    assert len(results) == 1
    assert results[0][0].memory_id == "m1"


def test_retrieve_category_filter(retrieval):
    e = np.array([1.0, 0.0])
    m1 = make_memory("m1", "fact1", embedding=e, category="preference")
    m2 = make_memory("m2", "fact2", embedding=e, category="fact")
    retrieval.add_memories([m1, m2])
    results = retrieval.retrieve(query_embedding=e, category_filter="fact")
    assert len(results) == 1
    assert results[0][0].memory_id == "m2"


def test_retrieve_min_score(retrieval):
    e = np.array([1.0, 0.0])
    m = make_memory("m1", "fact1", embedding=e, importance=0.0)
    retrieval.add_memory(m)
    results = retrieval.retrieve(query_embedding=e, min_score=1.0)
    assert len(results) == 0


def test_get_by_id_updates_access(retrieval):
    m = make_memory("m1", "fact1", access_count=0)
    retrieval.add_memory(m)
    retrieved = retrieval.get_by_id("m1")
    assert retrieved.access_count == 1
    assert retrieved.last_accessed >= m.last_accessed


def test_delete_memory(retrieval):
    m = make_memory("m1", "fact1")
    retrieval.add_memory(m)
    assert retrieval.delete_memory("m1") is True
    assert "m1" not in retrieval._memories


def test_get_stats(retrieval):
    m = make_memory("m1", "fact1")
    retrieval.add_memory(m)
    stats = retrieval.get_stats()
    assert stats["total_memories"] == 1
    assert stats["avg_importance"] == pytest.approx(0.5)
