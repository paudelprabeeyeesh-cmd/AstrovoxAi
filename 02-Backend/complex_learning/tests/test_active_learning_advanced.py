
from complex_learning.active_learning_advanced import AdvancedActiveLearner
import numpy as np


class TestAdvancedActiveLearner:
    def test_initialization(self):
        al = AdvancedActiveLearner(strategy='uncertainty', num_classes=2, acquisition='max_entropy', batch_size=1)
        assert al.strategy == 'uncertainty'
        assert al.num_classes == 2
        assert al.acquisition == 'max_entropy'
        assert al.batch_size == 1

    def test_initialize(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='max_entropy', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        initial_labels = np.full(12, -1, dtype=int)
        initial_labels[0] = 0
        initial_labels[1] = 1
        al.initialize(x, initial_labels)
        assert len(al.labeled_y) == 2
        assert len(al.unlabeled_indices) == 10

    def test_max_entropy(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='max_entropy', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])

        class MockModel:
            def predict_proba(self, x):
                return np.random.dirichlet(np.ones(2), size=len(x))

        model = MockModel()
        indices = al.query(model, batch_size=3)
        assert len(indices) == 3

    def test_margin(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='margin', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])

        class MockModel:
            def predict_proba(self, x):
                return np.random.dirichlet(np.ones(2), size=len(x))

        model = MockModel()
        indices = al.query(model, batch_size=3)
        assert len(indices) == 3

    def test_confidence(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='confidence', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])

        class MockModel:
            def predict_proba(self, x):
                return np.random.dirichlet(np.ones(2), size=len(x))

        model = MockModel()
        indices = al.query(model, batch_size=3)
        assert len(indices) == 3

    def test_random(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='random', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])

        class MockModel:
            pass

        model = MockModel()
        indices = al.query(model, batch_size=3)
        assert len(indices) == 3

    def test_update_labels(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='max_entropy', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])
        al.update_labels([5, 6], np.array([0, 1]))
        assert al.iteration_count == 1
        assert len(al.query_log) == 2

    def test_get_query_efficiency(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='max_entropy', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])
        efficiency = al.get_query_efficiency()
        assert "labeled_count" in efficiency
        assert "unlabeled_count" in efficiency
        assert "queries" in efficiency
        assert "strategy" in efficiency
        assert "iterations" in efficiency

    def test_evaluate(self):
        al = AdvancedActiveLearner(strategy='uncertainty', acquisition='max_entropy', num_classes=2)
        x = np.random.randn(12, 8).astype(np.float64)
        al.initialize(x, np.full(12, -1, dtype=int))
        al.labeled_x = x[:2]
        al.labeled_y = np.array([0, 1])

        class MockModel:
            def classify(self, x):
                return np.random.randint(0, 2, size=len(x))

        model = MockModel()
        x_test = np.random.randn(4, 8).astype(np.float64)
        y_test = np.random.randint(0, 2, size=4)
        result = al.evaluate(model, x_test, y_test)
        assert "accuracy" in result
        assert "f1" in result
        assert "precision" in result
        assert "recall" in result
