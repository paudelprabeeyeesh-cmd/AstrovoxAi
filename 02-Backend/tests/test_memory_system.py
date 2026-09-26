"""Tests for the unified memory system."""

from datetime import datetime, timezone

import pytest
from unittest.mock import patch

from app.services.memory_system import (
    MemorySystem,
    MemoryFragment,
    MemoryCategory,
    MemoryTier,
    ConflictStrategy,
    KnowledgeGraph,
    MemoryScorer,
    MemoryCompressor,
    ConflictDetector,
    get_memory_system,
)


@pytest.fixture
def memory_system():
    return MemorySystem()


class TestMemorySystem:
    def test_remember_creates_fragment(self, memory_system):
        frag = memory_system.remember("user-1", "Python is great", category=MemoryCategory.FACT)
        assert frag.user_id == "user-1"
        assert frag.content == "Python is great"
        assert frag.category == MemoryCategory.FACT
        assert frag.memory_id is not None

    def test_remember_user_preference(self, memory_system):
        frag = memory_system.remember("user-1", "theme:dark", category=MemoryCategory.USER_PREFERENCE, user_explicit=True)
        assert frag.category == MemoryCategory.USER_PREFERENCE
        assert frag.tier == MemoryTier.HIGH

    def test_recall_returns_memories(self, memory_system):
        memory_system.remember("user-1", "Python programming", category=MemoryCategory.FACT)
        memory_system.remember("user-1", "JavaScript is also great", category=MemoryCategory.FACT)
        results = memory_system.recall("user-1", query="Python")
        assert len(results) == 1
        assert "Python" in results[0].content

    def test_recall_by_category(self, memory_system):
        memory_system.remember("user-1", "fact one", category=MemoryCategory.FACT)
        memory_system.remember("user-1", "preference one", category=MemoryCategory.USER_PREFERENCE)
        results = memory_system.recall("user-1", category=MemoryCategory.USER_PREFERENCE)
        assert len(results) == 1
        assert results[0].category == MemoryCategory.USER_PREFERENCE

    def test_get_memory(self, memory_system):
        frag = memory_system.remember("user-1", "test content")
        fetched = memory_system.get_memory(frag.memory_id)
        assert fetched is not None
        assert fetched.content == "test content"

    def test_get_memory_not_found(self, memory_system):
        assert memory_system.get_memory("nonexistent") is None

    def test_edit_memory(self, memory_system):
        frag = memory_system.remember("user-1", "original content")
        updated = memory_system.edit_memory(frag.memory_id, "updated content")
        assert updated is not None
        assert updated.content == "updated content"
        assert updated.version == 2

    def test_edit_memory_not_found(self, memory_system):
        assert memory_system.edit_memory("nonexistent", "content") is None

    def test_delete_memory_soft(self, memory_system):
        frag = memory_system.remember("user-1", "to delete")
        assert memory_system.delete_memory(frag.memory_id, soft=True) is True
        assert memory_system.get_memory(frag.memory_id) is None

    def test_delete_memory_hard(self, memory_system):
        frag = memory_system.remember("user-1", "to hard delete")
        assert memory_system.delete_memory(frag.memory_id, soft=False) is True
        assert memory_system.get_memory(frag.memory_id) is None

    def test_delete_memory_not_found(self, memory_system):
        assert memory_system.delete_memory("nonexistent") is False

    def test_add_user_preference(self, memory_system):
        frag = memory_system.add_user_preference("user-1", "theme", "dark")
        assert frag.category == MemoryCategory.USER_PREFERENCE
        assert frag.metadata.get("preference_key") == "theme"
        assert frag.metadata.get("preference_value") == "dark"

    def test_get_user_preferences(self, memory_system):
        memory_system.add_user_preference("user-1", "theme", "dark")
        memory_system.add_user_preference("user-1", "language", "en")
        prefs = memory_system.get_user_preferences("user-1")
        assert len(prefs) >= 2

    def test_knowledge_graph(self, memory_system):
        memory_system.add_knowledge_node(KnowledgeNode(node_id="n1", name="Python", node_type="language"))
        memory_system.add_knowledge_node(KnowledgeNode(node_id="n2", name="Django", node_type="framework"))
        memory_system.add_knowledge_edge(KnowledgeEdge(edge_id="e1", source_id="n1", target_id="n2", relation="has_framework"))
        related = memory_system.get_related_knowledge("n1", depth=2)
        assert any(n.node_id == "n2" for n in related)

    def test_detect_conflicts(self, memory_system):
        memory_system.remember("user-1", "Python is great", category=MemoryCategory.FACT)
        memory_system.remember("user-1", "Python is terrible", category=MemoryCategory.FACT)
        conflicts = memory_system.detect_conflicts("user-1")
        assert len(conflicts) == 1

    def test_resolve_conflicts_newest(self, memory_system):
        memory_system.remember("user-1", "Python is great", category=MemoryCategory.FACT)
        frag2 = memory_system.remember("user-1", "Python is terrible", category=MemoryCategory.FACT)
        resolved = memory_system.resolve_conflicts("user-1", strategy=ConflictStrategy.NEWEST)
        assert len(resolved) == 1
        assert resolved[0].memory_id == frag2.memory_id

    def test_resolve_conflicts_merge(self, memory_system):
        memory_system.remember("user-1", "Python is great", category=MemoryCategory.FACT)
        memory_system.remember("user-1", "Python is terrible", category=MemoryCategory.FACT)
        resolved = memory_system.resolve_conflicts("user-1", strategy=ConflictStrategy.MERGE)
        assert len(resolved) == 1
        assert "---" in resolved[0].content

    def test_prioritize_context(self, memory_system):
        memory_system.remember("user-1", "important fact", category=MemoryCategory.FACT, importance=0.9)
        memory_system.remember("user-1", "less important fact", category=MemoryCategory.FACT, importance=0.2)
        prioritized = memory_system.prioritize_context("user-1", "fact", limit=2)
        assert len(prioritized) == 2
        assert prioritized[0].importance >= prioritized[1].importance

    def test_auto_compress(self, memory_system):
        long_content = " ".join(["word"] * 2000)
        frag = memory_system.remember("user-1", long_content, category=MemoryCategory.FACT)
        assert frag.compressed is True
        assert frag.summary is not None

    def test_decay_all(self, memory_system):
        memory_system.remember("user-1", "test1", category=MemoryCategory.FACT)
        memory_system.remember("user-1", "test2", category=MemoryCategory.FACT)
        count = memory_system.decay_all("user-1")
        assert count == 2

    def test_prune(self, memory_system):
        frag = memory_system.remember("user-1", "low importance", category=MemoryCategory.FACT, importance=0.01)
        removed = memory_system.prune("user-1", threshold=0.05)
        assert frag.memory_id in removed

    def test_get_stats(self, memory_system):
        memory_system.remember("user-1", "fact1", category=MemoryCategory.FACT)
        memory_system.remember("user-1", "pref1", category=MemoryCategory.USER_PREFERENCE)
        stats = memory_system.get_stats("user-1")
        assert stats["total"] >= 2
        assert "knowledge_graph" in stats

    def test_memory_scorer(self):
        scorer = MemoryScorer()
        score = scorer.score("important stuff", MemoryCategory.FACT, user_explicit=True)
        assert score > 0.5

    def test_memory_compressor(self):
        compressed = MemoryCompressor.compress(" ".join(["word"] * 1000))
        assert len(compressed) < len(" ".join(["word"] * 1000))

    def test_memory_compressor_summarize(self):
        summary = MemoryCompressor.summarize_for_context(" ".join(["word"] * 200), max_chars=50)
        assert len(summary) <= 53


class TestKnowledgeGraph:
    def test_add_node_and_edge(self):
        kg = KnowledgeGraph()
        kg.add_node(KnowledgeNode(node_id="n1", name="A", node_type="test"))
        kg.add_edge(KnowledgeEdge(edge_id="e1", source_id="n1", target_id="n2", relation="links"))
        assert kg.get_stats()["nodes"] == 1

    def test_get_neighbors(self):
        kg = KnowledgeGraph()
        kg.add_node(KnowledgeNode(node_id="n1", name="A", node_type="test"))
        kg.add_node(KnowledgeNode(node_id="n2", name="B", node_type="test"))
        kg.add_edge(KnowledgeEdge(edge_id="e1", source_id="n1", target_id="n2", relation="links"))
        neighbors = kg.get_neighbors("n1")
        assert "n2" in neighbors


class TestConflictDetector:
    def test_detect_conflict(self):
        detector = ConflictDetector()
        memories = [
            MemoryFragment("m1", "u1", "Python is great", MemoryType.LONG_TERM, MemoryTier.MEDIUM),
            MemoryFragment("m2", "u1", "Python is terrible", MemoryType.LONG_TERM, MemoryTier.MEDIUM),
        ]
        conflicts = detector.detect_conflicts(memories)
        assert len(conflicts) == 1

    def test_no_conflict_same_content(self):
        detector = ConflictDetector()
        memories = [
            MemoryFragment("m1", "u1", "Python is great", MemoryType.LONG_TERM, MemoryTier.MEDIUM),
            MemoryFragment("m2", "u1", "Python is great", MemoryType.LONG_TERM, MemoryTier.MEDIUM),
        ]
        conflicts = detector.detect_conflicts(memories)
        assert len(conflicts) == 0

    def test_resolve_newest(self):
        detector = ConflictDetector()
        a = MemoryFragment("m1", "u1", "old", MemoryType.LONG_TERM, MemoryTier.MEDIUM, updated_at=datetime.now(timezone.utc))
        b = MemoryFragment("m2", "u1", "new", MemoryType.LONG_TERM, MemoryTier.MEDIUM, updated_at=datetime.now(timezone.utc))
        winner = detector.resolve_conflict(a, b, ConflictStrategy.NEWEST)
        assert winner.memory_id == b.memory_id
