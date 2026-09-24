
from complex_learning.active_learning_advanced import ActiveLearner
import numpy as np


class TestActiveLearner:
    def test_initialization(self):
        al = ActiveLearner(input_dim=8)
        assert al.input_dim == 8
        assert al.hidden_dim == 64
        assert al.output_dim == 5
        assert al.batch_size == 10
        assert len(al.params) == 4

    def test_fit(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2])
        al.fit(x, y)
        assert len(al.loss_history) == 5

    def test_set_dataset(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = [0, 1, 2, 3]
        al.set_dataset(x, labeled)
        assert len(al.labeled_indices) == 4
        assert len(al.unlabeled_indices) == 8

    def test_entropy_sampling(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        scores = al.entropy_sampling(x_unlabeled)
        assert scores.shape == (8,)
        assert all(s >= 0.0 for s in scores)

    def test_margin_sampling(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        scores = al.margin_sampling(x_unlabeled)
        assert scores.shape == (8,)

    def test_uncertainty_sampling(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        for method in ["entropy", "margin", "combined"]:
            scores = al.uncertainty_sampling(x_unlabeled, method=method)
            assert scores.shape == (8,)

    def test_expected_model_change(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        scores = al.expected_model_change(x_unlabeled)
        assert scores.shape == (8,)

    def test_query_by_committee(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        scores = al.query_by_committee(x_unlabeled, num_committee=3)
        assert scores.shape == (8,)

    def test_select_samples_entropy(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        selected = al.select_samples(x_unlabeled, method="entropy", k=3)
        assert selected.shape == (3,)
        assert all(0 <= s < 8 for s in selected)

    def test_select_samples_core_set(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_labeled = x[labeled]
        x_unlabeled = x[al.unlabeled_indices]
        selected = al.select_samples(x_labeled, x_unlabeled, method="core_set", k=3)
        assert selected.shape == (3,)

    def test_select_samples_vaal(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_labeled = x[labeled]
        x_unlabeled = x[al.unlabeled_indices]
        selected = al.select_samples(x_labeled, x_unlabeled, method="vaal", k=3)
        assert selected.shape == (3,)

    def test_select_samples_committee(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(12, 8).astype(np.float64)
        labeled = list(range(4))
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        selected = al.select_samples(x_unlabeled, method="committee", k=3)
        assert selected.shape == (3,)

    def test_get_active_report(self):
        al = ActiveLearner(input_dim=8)
        al.set_dataset(np.random.randn(12, 8), [0, 1])
        report = al.get_active_report()
        assert "num_labeled" in report
        assert "num_unlabeled" in report
        assert "num_steps" in report

    def test_k_all(self):
        al = ActiveLearner(input_dim=8)
        x = np.random.randn(5, 8).astype(np.float64)
        labeled = [0]
        al.set_dataset(x, labeled)
        x_unlabeled = x[al.unlabeled_indices]
        selected = al.select_samples(x_unlabeled, method="entropy", k=10)
        assert selected.shape == (4,)
