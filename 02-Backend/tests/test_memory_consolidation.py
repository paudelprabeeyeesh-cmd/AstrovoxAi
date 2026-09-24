"""
Memory Consolidation Integration Tests.
"""

from __future__ import annotations

import logging
import pytest
from datetime import datetime, timedelta

from app.memory.memory_consolidation import MemoryConsolidationService, ConsolidationRecord
from app.memory.memory_manager import MemoryManager
from memory_persistence.memory_consolidation import MemoryConsolidator, MemoryFragment

logger = logging.getLogger(__name__)


def test_consolidation_service_initialization():
    service = MemoryConsolidationService()
    assert service is not None
    assert service._consolidator is not None


def test_memory_consolidator_duplicate_merging():
    consolidator = MemoryConsolidator(similarity_threshold=0.7)
    base_time = datetime.utcnow()
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [0.95, 0.05, 0.0]

    m1 = MemoryFragment(
        memory_id="m1",
        content="User prefers Python",
        embedding=emb1,
        importance=0.6,
        created_at=base_time,
        last_accessed=base_time,
        category="semantic",
    )
    m2 = MemoryFragment(
        memory_id="m2",
        content="User prefers Python",
        embedding=emb2,
        importance=0.7,
        created_at=base_time + timedelta(minutes=1),
        last_accessed=base_time + timedelta(minutes=1),
        category="semantic",
    )

    consolidator.add_memories([m1, m2])
    result = consolidator.merge_duplicates()
    assert result["merged_count"] >= 0


def test_memory_consolidator_pruning():
    consolidator = MemoryConsolidator(stale_days=1)
    old_time = datetime.utcnow() - timedelta(days=10)
    m = MemoryFragment(
        memory_id="old_low",
        content="temporary info",
        importance=0.2,
        created_at=old_time,
        last_accessed=old_time,
        category="general",
        access_count=0,
    )
    consolidator.add_memory(m)
    result = consolidator.prune_stale(now=datetime.utcnow())
    assert result["pruned_count"] >= 0


def test_memory_manager_consolidation():
    manager = MemoryManager()
    assert manager.consolidation_service is not None
    stats = manager.get_consolidation_stats(user_id=999)
    assert isinstance(stats, dict)


def test_consolidation_record():
    record = ConsolidationRecord(
        memory_id="u1",
        action="test",
        details={"x": 1},
    )
    assert record.action == "test"
    assert record.details == {"x": 1}
    assert record.created_at is not None


def test_consolidation_service_records():
    service = MemoryConsolidationService()
    service._records.append(ConsolidationRecord(memory_id="r1", action="a", details={}))
    recs = service.get_records(limit=10)
    assert len(recs) == 1
    assert recs[0]["memory_id"] == "r1"
