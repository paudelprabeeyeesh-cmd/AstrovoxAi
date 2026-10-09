from __future__ import annotations

import pytest
import numpy as np
from datetime import datetime, timedelta

from memory_persistence.memory_pruning import Memory, MemoryPruner


def make_memory(memory_id, content, embedding=None, importance=0.5, created_at=None, is_deleted=False, access_count=0):
    return Memory(
        memory_id=memory_id,
        content=content,
        embedding=embedding,
        importance=importance,
        created_at=created_at or datetime.utcnow(),
        is_deleted=is_deleted,
        access_count=access_count,
    )


@pytest.fixture
def pruner():
    return MemoryPruner(stale_threshold_days=1)


def test_add_memory(pruner):
    m = make_memory("m1", "fact1")
    assert pruner.add_memory(m) == "m1"
    assert "m1" in pruner._memories


def test_prune_stale(pruner):
    old = datetime.utcnow() - timedelta(days=10)
    m = make_memory("m1", "old fact", created_at=old, access_count=0)
    pruner.add_memory(m)
    pruned = pruner.prune_stale(now=datetime.utcnow())
    assert "m1" in pruned
    assert pruner._memories["m1"].is_deleted is True


def test_prune_stale_does_not_prune_recent(pruner):
    m = make_memory("m1", "recent fact", access_count=5)
    pruner.add_memory(m)
    pruned = pruner.prune_stale(now=datetime.utcnow())
    assert "m1" not in pruned
    assert pruner._memories["m1"].is_deleted is False


def test_prune_contradictions(pruner):
    e = np.ones(4)
    m1 = make_memory("m1", "I like cats", embedding=e, created_at=datetime.utcnow() - timedelta(hours=2))
    m2 = make_memory("m2", "I do not like cats", embedding=e, created_at=datetime.utcnow())
    pruner.add_memories([m1, m2])
    resolutions = pruner.prune_contradictions()
    assert len(resolutions) == 1
    assert pruner._memories["m1"].is_deleted is True
    assert pruner._memories["m1"].superseded_by == "m2"


def test_prune_redundant(pruner):
    e = np.ones(4)
    m1 = make_memory("m1", "fact", embedding=e, importance=0.9)
    m2 = make_memory("m2", "fact", embedding=e, importance=0.5)
    pruner.add_memories([m1, m2])
    pruned = pruner.prune_redundant()
    assert len(pruned) == 1
    assert pruned[0][0] == "m2"
    assert pruner._memories["m2"].is_deleted is True


def test_prune_all(pruner):
    old = datetime.utcnow() - timedelta(days=10)
    m = make_memory("m1", "old fact", created_at=old, access_count=0)
    pruner.add_memory(m)
    summary = pruner.prune_all(now=datetime.utcnow())
    assert summary["stale_pruned"] == 1


def test_get_active_memories(pruner):
    m = make_memory("m1", "fact")
    pruner.add_memory(m)
    active = pruner.get_active_memories()
    assert len(active) == 1
    m.is_deleted = True
    active = pruner.get_active_memories()
    assert len(active) == 0
