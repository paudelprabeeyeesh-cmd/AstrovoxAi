import numpy as np
import pytest
from adaptive_learning.active_learning import ActiveLearner


class DummyModel:
    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return np.random.rand(len(x), 2)


class TestActiveLearner:
    def test_initialization(self):
        al = ActiveLearner(strategy="uncertainty")
        assert al.strategy == "uncertainty"
        assert len(al.labeled_y) == 0

    def test_initialize(self):
        al = ActiveLearner()
        x = np.random.randn(20, 4)
        al.initialize(x)
        assert len(al.unlabeled_indices) == 20

    def test_query_uncertainty(self):
        al = ActiveLearner(strategy="uncertainty")
        x = np.random.randn(20, 4)
        al.initialize(x)
        model = DummyModel()
        indices = al.query(model, batch_size=5)
        assert len(indices) == 5
        assert all(isinstance(i, int) for i in indices)

    def test_query_entropy(self):
        al = ActiveLearner(strategy="entropy")
        x = np.random.randn(20, 4)
        al.initialize(x)
        model = DummyModel()
        indices = al.query(model, batch_size=5)
        assert len(indices) == 5

    def test_query_margin(self):
        al = ActiveLearner(strategy="margin")
        x = np.random.randn(20, 4)
        al.initialize(x)
        model = DummyModel()
        indices = al.query(model, batch_size=5)
        assert len(indices) == 5

    def test_query_random(self):
        al = ActiveLearner(strategy="random")
        x = np.random.randn(20, 4)
        al.initialize(x)
        indices = al.query(None, batch_size=5)
        assert len(indices) == 5

    def test_update_labels(self):
        al = ActiveLearner()
        x = np.random.randn(20, 4)
        al.initialize(x)
        indices = al.query(None, batch_size=3)
        labels = np.array([0, 1, 0])
        al.update_labels(indices, labels)
        assert len(al.query_log) == 3

    def test_get_query_efficiency(self):
        al = ActiveLearner()
        x = np.random.randn(20, 4)
        al.initialize(x)
        report = al.get_query_efficiency()
        assert report["strategy"] == "uncertainty"
        assert report["unlabeled_count"] == 20

    def test_unknown_strategy_raises(self):
        al = ActiveLearner(strategy="unknown")
        x = np.random.randn(10, 4)
        al.initialize(x)
        with pytest.raises(ValueError, match="Unknown strategy"):
            al.query(None, batch_size=1)
