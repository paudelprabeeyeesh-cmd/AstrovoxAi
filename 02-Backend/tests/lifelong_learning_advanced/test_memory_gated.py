import numpy as np

from lifelong_learning_advanced.memory_gated import MemoryGated, MemoryGateConfig


class TestMemoryGated:
    def test_admit_high_novelty(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=0.0))
        emb = np.array([1.0, 0.0, 0.0])
        result = mg.admit("k1", emb, importance=1.0)
        assert result["admitted"] is True

    def test_reject_low_novelty(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=1.5, importance_threshold=0.0))
        emb = np.array([1.0, 0.0, 0.0])
        result = mg.admit("k1", emb, importance=1.0)
        assert result["admitted"] is False
        assert result["reason"] == "low_novelty"

    def test_reject_low_importance(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=2.0))
        emb = np.array([1.0, 0.0, 0.0])
        result = mg.admit("k1", emb, importance=0.1)
        assert result["admitted"] is False
        assert result["reason"] == "low_importance"

    def test_access(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=0.0))
        mg.admit("k1", np.array([1.0, 0.0]), importance=1.0)
        entry = mg.access("k1")
        assert entry is not None
        assert entry.access_count == 1

    def test_access_missing(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=0.0))
        assert mg.access("missing") is None

    def test_capacity_enforcement(self):
        mg = MemoryGated(config=MemoryGateConfig(capacity=2, novelty_threshold=0.0, importance_threshold=0.0))
        mg.admit("k1", np.array([1.0, 0.0]), importance=1.0)
        mg.admit("k2", np.array([0.0, 1.0]), importance=1.0)
        mg.admit("k3", np.array([1.0, 1.0]), importance=1.0)
        assert len(mg._memories) <= 2

    def test_query(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=0.0))
        mg.admit("k1", np.array([1.0, 0.0]), importance=1.0)
        mg.admit("k2", np.array([0.0, 1.0]), importance=1.0)
        results = mg.query(np.array([1.0, 0.0]), top_k=1)
        assert len(results) == 1
        assert results[0][0] == "k1"

    def test_query_empty(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=0.0))
        assert mg.query(np.array([1.0, 0.0])) == []

    def test_get_stats(self):
        mg = MemoryGated(config=MemoryGateConfig(novelty_threshold=0.0, importance_threshold=0.0))
        mg.admit("k1", np.array([1.0, 0.0]), importance=1.0)
        mg.admit("k1", np.array([1.0, 0.0]), importance=1.0)
        mg.admit("k2", np.array([0.0, 1.0]), importance=0.1)
        stats = mg.get_stats()
        assert stats["admitted"] >= 1
        assert stats["used"] >= 1
