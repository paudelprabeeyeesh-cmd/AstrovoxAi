import numpy as np
import pytest
from complex_learning.active_learning_advanced import AdvancedActiveLearner


class TestAdvancedActiveLearner:
    def test_initialization(self):
        al = AdvancedActiveLearner(strategy="uncertainty", num_classes=3, acquisition="max_entropy")
        assert al.acquisition == "max_entropy"
        assert al.num_classes == 3

    def test_initialize(self):
        al = AdvancedActiveLearner()
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        assert len(al.unlabeled_indices) == 20
        assert len(al.labeled_y) == 0

    def test_initialize_with_labels(self):
        al = AdvancedActiveLearner()
        x = np.random.randn(10, 8)
        labels = np.array([0, 1, -1, -1, -1, -1, -1, -1, -1, -1])
        al.initialize(x, initial_labels=labels)
        assert len(al.labeled_y) == 2
        assert len(al.unlabeled_indices) == 8

    def test_query_max_entropy(self):
        al = AdvancedActiveLearner(acquisition="max_entropy")
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        indices = al.query(None, batch_size=3)
        assert len(indices) == 3
        assert all(i in al.unlabeled_indices for i in indices)

    def test_query_bald(self):
        al = AdvancedActiveLearner(acquisition="bald")
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        indices = al.query(None, batch_size=3)
        assert len(indices) == 3

    def test_query_margin(self):
        al = AdvancedActiveLearner(acquisition="margin")
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        indices = al.query(None, batch_size=3)
        assert len(indices) == 3

    def test_query_confidence(self):
        al = AdvancedActiveLearner(acquisition="confidence")
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        indices = al.query(None, batch_size=3)
        assert len(indices) == 3

    def test_query_random(self):
        al = AdvancedActiveLearner(acquisition="random")
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        indices = al.query(None, batch_size=3)
        assert len(indices) == 3

    def test_query_with_proba_model(self):
        al = AdvancedActiveLearner(acquisition="max_entropy")

        class Model:
            def predict_proba(self, x):
                return np.random.rand(len(x), al.num_classes)

        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        indices = al.query(Model(), batch_size=3)
        assert len(indices) == 3

    def test_update_labels(self):
        al = AdvancedActiveLearner()
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        al.update_labels(al.unlabeled_indices[:5].tolist(), np.array([0, 1, 0, 1, 0]))
        assert len(al.unlabeled_indices) == 15
        assert al.iteration_count == 1

    def test_get_query_efficiency(self):
        al = AdvancedActiveLearner()
        x = np.random.randn(20, 8)
        al.initialize(x, initial_labels=np.array([-1] * 20))
        eff = al.get_query_efficiency()
        assert eff["labeled_count"] == 0
        assert eff["unlabeled_count"] == 20
        assert eff["strategy"] == "max_entropy"

    def test_evaluate(self):
        al = AdvancedActiveLearner()

        class Model:
            def classify(self, x):
                return np.random.randint(0, 2, size=len(x))

        x_test = np.random.randn(10, 8)
        y_test = np.random.randint(0, 2, size=10)
        result = al.evaluate(Model(), x_test, y_test)
        assert "accuracy" in result
        assert "f1" in result
