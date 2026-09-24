import numpy as np
import pytest
from complex_learning.few_shot_advanced import AdvancedPrototypicalNetworks, RelationNetwork, Episode


class TestAdvancedPrototypicalNetworks:
    def test_initialization(self):
        apn = AdvancedPrototypicalNetworks(embedding_dim=64, distance_metric="euclidean")
        assert apn.embedding_dim == 64
        assert len(apn.prototypes) == 0

    def test_compute_prototypes(self):
        apn = AdvancedPrototypicalNetworks(embedding_dim=32)
        x = np.random.randn(20, 8)
        y = np.array([0] * 10 + [1] * 10)
        prototypes = apn.compute_prototypes(x, y)
        assert 0 in prototypes
        assert 1 in prototypes
        assert prototypes[0].shape == (32,)

    def test_classify_euclidean(self):
        apn = AdvancedPrototypicalNetworks(embedding_dim=32, distance_metric="euclidean")
        support_x = np.random.randn(10, 8)
        support_y = np.array([0] * 5 + [1] * 5)
        apn.compute_prototypes(support_x, support_y)
        query_x = np.random.randn(4, 8)
        preds = apn.classify(query_x)
        assert preds.shape == (4,)
        assert set(np.unique(preds)).issubset({0, 1})

    def test_classify_cosine(self):
        apn = AdvancedPrototypicalNetworks(embedding_dim=32, distance_metric="cosine")
        support_x = np.random.randn(10, 8)
        support_y = np.array([0] * 5 + [1] * 5)
        apn.compute_prototypes(support_x, support_y)
        query_x = np.random.randn(4, 8)
        preds = apn.classify(query_x)
        assert preds.shape == (4,)

    def test_train_episode(self):
        apn = AdvancedPrototypicalNetworks(embedding_dim=32)
        episode = Episode(support_x=np.random.randn(8, 8), support_y=np.array([0] * 4 + [1] * 4),
                          query_x=np.random.randn(4, 8), query_y=np.array([0, 0, 1, 1]), n_way=2, k_shot=4)
        result = apn.train_episode(episode)
        assert "loss" in result
        assert "accuracy" in result

    def test_evaluate_episode(self):
        apn = AdvancedPrototypicalNetworks(embedding_dim=32)
        episode = Episode(support_x=np.random.randn(8, 8), support_y=np.array([0] * 4 + [1] * 4),
                          query_x=np.random.randn(4, 8), query_y=np.array([0, 0, 1, 1]), n_way=2, k_shot=4)
        result = apn.evaluate_episode(episode)
        assert "accuracy" in result
        assert "probs" in result


class TestRelationNetwork:
    def test_initialization(self):
        rn = RelationNetwork(embedding_dim=32, relation_dim=64)
        assert rn.embedding_dim == 32
        assert rn.eW.shape == (64, 64)

    def test_score_samples(self):
        rn = RelationNetwork(embedding_dim=32)
        support_x = np.random.randn(6, 8)
        support_y = np.array([0] * 3 + [1] * 3)
        query_x = np.random.randn(2, 8)
        scores = rn.score_samples(support_x, support_y, query_x)
        assert scores.shape == (2, 6)

    def test_predict(self):
        rn = RelationNetwork(embedding_dim=32)
        support_x = np.random.randn(6, 8)
        support_y = np.array([0] * 3 + [1] * 3)
        query_x = np.random.randn(2, 8)
        preds = rn.predict(support_x, support_y, query_x)
        assert preds.shape == (2,)
        assert set(np.unique(preds)).issubset({0, 1})

    def test_train_step(self):
        rn = RelationNetwork(embedding_dim=32)
        support_x = np.random.randn(6, 8)
        support_y = np.array([0] * 3 + [1] * 3)
        query_x = np.random.randn(2, 8)
        query_y = np.array([0, 1])
        loss = rn.train_step(support_x, support_y, query_x, query_y, lr=0.01)
        assert isinstance(loss, float)
        assert len(rn.loss_history) == 1

    def test_evaluate_step(self):
        rn = RelationNetwork(embedding_dim=32)
        support_x = np.random.randn(6, 8)
        support_y = np.array([0] * 3 + [1] * 3)
        query_x = np.random.randn(2, 8)
        query_y = np.array([0, 1])
        result = rn.evaluate_step(support_x, support_y, query_x, query_y)
        assert "accuracy" in result
