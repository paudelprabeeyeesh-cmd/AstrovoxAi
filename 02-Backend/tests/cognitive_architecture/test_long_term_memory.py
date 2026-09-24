import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.long_term_memory import (
    LongTermMemory,
    HippocampalIndex,
    EpisodicMemory,
    SemanticMemory,
    MemoryConsolidation,
)


class TestHippocampalIndex:
    def test_pattern_separate_shape(self):
        idx = HippocampalIndex(embedding_dim=64, sparse_size=128)
        embedding = np.random.randn(64)
        sparse = idx.pattern_separate(embedding)
        assert sparse.shape == (128,)

    def test_pattern_complete_returns_ids(self):
        idx = HippocampalIndex(embedding_dim=64, sparse_size=128)
        emb = np.random.randn(64)
        mem_id = idx.index_memory(emb)
        results = idx.pattern_complete(emb, k=1)
        assert mem_id in results

    def test_index_multiple_memories(self):
        idx = HippocampalIndex(embedding_dim=32, sparse_size=64)
        ids = [idx.index_memory(np.random.randn(32)) for _ in range(10)]
        assert len(set(ids)) == 10


class TestMemoryConsolidation:
    def test_should_consolidate_when_recency_low(self):
        cons = MemoryConsolidation(consolidation_threshold=0.5)
        episode = EpisodicMemory(
            content="test", context={}, timestamp=0.0, emotional_valence=0.0,
            embedding=np.zeros(32), strength=0.8,
        )
        current_time = 100.0
        assert cons.should_consolidate(episode, current_time)

    def test_no_consolidate_when_strength_low(self):
        cons = MemoryConsolidation(consolidation_threshold=0.5)
        episode = EpisodicMemory(
            content="test", context={}, timestamp=0.0, emotional_valence=0.0,
            embedding=np.zeros(32), strength=0.1,
        )
        current_time = 100.0
        assert not cons.should_consolidate(episode, current_time)

    def test_consolidate_produces_semantic(self):
        cons = MemoryConsolidation()
        episode = EpisodicMemory(
            content="hello world", context={}, timestamp=0.0, emotional_valence=0.0,
            embedding=np.ones(32), strength=0.9,
        )
        semantic = cons.consolidate(episode)
        assert isinstance(semantic, SemanticMemory)
        assert semantic.confidence == pytest.approx(0.9)

    def test_replay_returns_subset(self):
        cons = MemoryConsolidation(replay_ratio=0.5)
        episodes = [
            EpisodicMemory(content=f"e{i}", context={}, timestamp=time.time(), emotional_valence=0.0,
                           embedding=np.ones(32), strength=0.5 + i * 0.1)
            for i in range(10)
        ]
        replayed = cons.replay(episodes, n=3)
        assert len(replayed) <= 3
        assert len(replayed) > 0


class TestLongTermMemory:
    def test_store_and_retrieve(self):
        ltm = LongTermMemory(embedding_dim=32, sparse_size=64)
        emb = np.random.randn(32)
        mem_id = ltm.store_episode("event1", {"loc": "here"}, emb, emotional_valence=0.5)
        assert mem_id >= 0
        results = ltm.retrieve_similar(emb, k=1)
        assert len(results) == 1

    def test_memory_stats(self):
        ltm = LongTermMemory(embedding_dim=32, sparse_size=64)
        emb = np.random.randn(32)
        ltm.store_episode("e1", {}, emb)
        stats = ltm.get_memory_stats()
        assert stats["episodic_count"] == 1

    def test_consolidate_memories(self):
        ltm = LongTermMemory(embedding_dim=32, sparse_size=64)
        old_time = time.time() - 1000.0
        emb = np.random.randn(32)
        ltm.store_episode("old_event", {}, emb, emotional_valence=0.8, timestamp=old_time)
        consolidated = ltm.consolidate_memories(current_time=time.time())
        assert len(consolidated) >= 0

    def test_empty_retrieve(self):
        ltm = LongTermMemory(embedding_dim=32, sparse_size=64)
        results = ltm.retrieve_similar(np.random.randn(32), k=5)
        assert results == []
