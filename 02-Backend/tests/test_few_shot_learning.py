import numpy as np
import pytest
from adaptive_learning.few_shot_learning import PrototypicalNetworks, MatchingNetworks, Episode


class TestPrototypicalNetworks:
    def test_initialization(self):
        pn = PrototypicalNetworks(embedding_dim=64)
        assert pn.embedding_dim == 64
        assert len(pn.prototypes) == 0

    def test_compute_prototypes(self):
        pn = PrototypicalNetworks(embedding_dim=32)
        x = np.random.randn(20, 8)
        y = np.array([0] * 10 + [1] * 10)
        prototypes = pn.compute_prototypes(x, y)
        assert 0 in prototypes
        assert 1 in prototypes
        assert prototypes[0].shape == (32,)

    def test_classify(self):
        pn = PrototypicalNetworks(embedding_dim=32)
        support_x = np.random.randn(10, 8)
        support_y = np.array([0] * 5 + [1] * 5)
        query_x = np.random.randn(4, 8)
        prototypes = pn.compute_prototypes(support_x, support_y)
        preds = pn.classify(query_x, prototypes)
        assert preds.shape == (4,)
        assert set(np.unique(preds)).issubset({0, 1})

    def test_train_episode(self):
        pn = PrototypicalNetworks(embedding_dim=32)
        episode = Episode(
            support_x=np.random.randn(10, 8),
            support_y=np.array([0] * 5 + [1] * 5),
            query_x=np.random.randn(4, 8),
            query_y=np.array([0, 0, 1, 1]),
            n_way=2,
            k_shot=5,
        )
        result = pn.train_episode(episode)
        assert "accuracy" in result
        assert 0.0 <= result["accuracy"] <= 1.0

    def test_evaluate_episode(self):
        pn = PrototypicalNetworks(embedding_dim=32)
        episode = Episode(
            support_x=np.random.randn(10, 8),
            support_y=np.array([0] * 5 + [1] * 5),
            query_x=np.random.randn(4, 8),
            query_y=np.array([0, 0, 1, 1]),
            n_way=2,
            k_shot=5,
        )
        result = pn.evaluate_episode(episode)
        assert "accuracy" in result
        assert "predictions" in result


class TestMatchingNetworks:
    def test_initialization(self):
        mn = MatchingNetworks(embedding_dim=64)
        assert mn.embedding_dim == 64
        assert mn.support_set is None

    def test_set_support_and_classify(self):
        mn = MatchingNetworks(embedding_dim=32)
        support_x = np.random.randn(10, 8)
        support_y = np.array([0] * 5 + [1] * 5)
        mn.set_support(support_x, support_y)
        query_x = np.random.randn(4, 8)
        preds = mn.classify(query_x)
        assert preds.shape == (4,)
        assert set(np.unique(preds)).issubset({0, 1})
