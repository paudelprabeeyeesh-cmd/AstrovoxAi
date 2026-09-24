import numpy as np
import pytest
from advanced_learning.few_shot_advanced import PrototypicalNetwork, FewShotConfig


class TestPrototypicalNetwork:
    def test_initialization(self):
        config = FewShotConfig(input_dim=32, num_classes=5)
        pn = PrototypicalNetwork(config)
        assert pn.config.input_dim == 32
        assert pn.config.num_classes == 5
        assert pn.config.num_support == 5
        assert len(pn.loss_history) == 0

    def test_embed(self):
        config = FewShotConfig(input_dim=32, num_classes=5, embedding_dim=64)
        pn = PrototypicalNetwork(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = pn._embed(x)
        assert z.shape == (8, 64)

    def test_compute_prototypes(self):
        config = FewShotConfig(input_dim=32, num_classes=3, embedding_dim=64)
        pn = PrototypicalNetwork(config)
        support_emb = np.random.randn(15, 64).astype(np.float64)
        support_labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 0, 1, 2, 0, 1, 2])
        prototypes = pn._compute_prototypes(support_emb, support_labels)
        assert prototypes.shape == (3, 64)

    def test_compute_distances_euclidean(self):
        config = FewShotConfig(input_dim=32, num_classes=3, embedding_dim=64, distance_metric="euclidean")
        pn = PrototypicalNetwork(config)
        query_emb = np.random.randn(5, 64).astype(np.float64)
        prototypes = np.random.randn(3, 64).astype(np.float64)
        distances = pn._compute_distances(query_emb, prototypes)
        assert distances.shape == (5, 3)

    def test_compute_distances_cosine(self):
        config = FewShotConfig(input_dim=32, num_classes=3, embedding_dim=64, distance_metric="cosine")
        pn = PrototypicalNetwork(config)
        query_emb = np.random.randn(5, 64).astype(np.float64)
        prototypes = np.random.randn(3, 64).astype(np.float64)
        distances = pn._compute_distances(query_emb, prototypes)
        assert distances.shape == (5, 3)

    def test_train_episode(self):
        config = FewShotConfig(input_dim=32, num_classes=5, num_support=5, num_query=15)
        pn = PrototypicalNetwork(config)
        support_x = np.random.randn(25, 32).astype(np.float64)
        support_y = np.repeat(np.arange(5), 5).astype(np.int64)
        query_x = np.random.randn(75, 32).astype(np.float64)
        query_y = np.repeat(np.arange(5), 15).astype(np.int64)
        result = pn.train_episode(support_x, support_y, query_x, query_y)
        assert "loss" in result
        assert "accuracy" in result
        assert len(pn.loss_history) == 1

    def test_predict(self):
        config = FewShotConfig(input_dim=32, num_classes=5, num_support=5, num_query=15)
        pn = PrototypicalNetwork(config)
        support_x = np.random.randn(25, 32).astype(np.float64)
        support_y = np.repeat(np.arange(5), 5).astype(np.int64)
        query_x = np.random.randn(15, 32).astype(np.float64)
        preds = pn.predict(support_x, support_y, query_x)
        assert preds.shape == (15,)
        assert all(0 <= p < 5 for p in preds)

    def test_get_few_shot_report(self):
        config = FewShotConfig(input_dim=32, num_classes=5)
        pn = PrototypicalNetwork(config)
        support_x = np.random.randn(25, 32).astype(np.float64)
        support_y = np.repeat(np.arange(5), 5).astype(np.int64)
        query_x = np.random.randn(15, 32).astype(np.float64)
        query_y = np.repeat(np.arange(5), 15).astype(np.int64)
        pn.train_episode(support_x, support_y, query_x, query_y)
        report = pn.get_few_shot_report()
        assert "num_episodes" in report
        assert report["num_classes"] == 5
