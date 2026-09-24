
from complex_learning.few_shot_advanced import AdvancedPrototypicalNetworks, RelationNetwork, Episode
import numpy as np


class TestAdvancedPrototypicalNetworks:
    def test_initialization(self):
        pn = AdvancedPrototypicalNetworks(embedding_dim=32)
        assert pn.embedding_dim == 32
        assert pn.distance_metric == "euclidean"
        assert pn.prototypes == {}

    def test_compute_prototypes(self):
        np.random.seed(42)
        pn = AdvancedPrototypicalNetworks(embedding_dim=16)
        x = np.random.randn(8, 4).astype(np.float64)
        y = np.array([0, 0, 1, 1, 2, 2, 2, 2])
        prototypes = pn.compute_prototypes(x, y)
        assert len(prototypes) == 3
        assert 0 in prototypes
        assert 1 in prototypes
        assert 2 in prototypes

    def test_classify(self):
        np.random.seed(42)
        pn = AdvancedPrototypicalNetworks(embedding_dim=16)
        x_supp = np.random.randn(6, 4).astype(np.float64)
        y_supp = np.array([0, 0, 1, 1, 2, 2])
        pn.compute_prototypes(x_supp, y_supp)
        x_q = np.random.randn(3, 4).astype(np.float64)
        preds = pn.classify(x_q)
        assert preds.shape == (3,)
        assert all(p in [0, 1, 2] for p in preds)

    def test_train_episode(self):
        np.random.seed(42)
        pn = AdvancedPrototypicalNetworks(embedding_dim=16)
        ep = Episode(
            np.random.randn(6, 4).astype(np.float64),
            np.array([0, 0, 1, 1, 2, 2]),
            np.random.randn(3, 4).astype(np.float64),
            np.array([0, 1, 2]),
            n_way=3, k_shot=1,
        )
        result = pn.train_episode(ep)
        assert "loss" in result
        assert "accuracy" in result
        assert "n_query" in result
        assert result["n_query"] == 3

    def test_evaluate_episode(self):
        np.random.seed(42)
        pn = AdvancedPrototypicalNetworks(embedding_dim=16)
        x_supp = np.random.randn(6, 4).astype(np.float64)
        y_supp = np.array([0, 0, 1, 1, 2, 2])
        pn.compute_prototypes(x_supp, y_supp)
        ep = Episode(
            x_supp.copy(), y_supp.copy(),
            np.random.randn(3, 4).astype(np.float64),
            np.array([0, 1, 2]),
            n_way=3, k_shot=1,
        )
        result = pn.evaluate_episode(ep)
        assert "accuracy" in result
        assert "predictions" in result

    def test_cosine_distance(self):
        pn = AdvancedPrototypicalNetworks(embedding_dim=16, distance_metric="cosine")
        x = np.random.randn(4, 4).astype(np.float64)
        y = np.array([0, 0, 1, 1])
        pn.compute_prototypes(x, y)
        x_q = np.random.randn(2, 4).astype(np.float64)
        preds = pn.classify(x_q)
        assert preds.shape == (2,)


class TestRelationNetwork:
    def test_initialization(self):
        rn = RelationNetwork(embedding_dim=16, relation_dim=32)
        assert rn.embedding_dim == 16
        assert rn.relation_dim == 32

    def test_score_samples(self):
        np.random.seed(42)
        rn = RelationNetwork(embedding_dim=16)
        supp_x = np.random.randn(4, 8).astype(np.float64)
        supp_y = np.array([0, 1, 0, 1])
        q_x = np.random.randn(2, 8).astype(np.float64)
        scores = rn.score_samples(supp_x, supp_y, q_x)
        assert scores.shape == (2, 4)

    def test_predict(self):
        np.random.seed(42)
        rn = RelationNetwork(embedding_dim=16)
        supp_x = np.random.randn(4, 8).astype(np.float64)
        supp_y = np.array([0, 1, 0, 1])
        q_x = np.random.randn(2, 8).astype(np.float64)
        preds = rn.predict(supp_x, supp_y, q_x)
        assert preds.shape == (2,)
        assert all(p in [0, 1] for p in preds)

    def test_train_step(self):
        np.random.seed(42)
        rn = RelationNetwork(embedding_dim=16)
        supp_x = np.random.randn(4, 8).astype(np.float64)
        supp_y = np.array([0, 1, 0, 1])
        q_x = np.random.randn(2, 8).astype(np.float64)
        q_y = np.array([0, 1])
        loss = rn.train_step(supp_x, supp_y, q_x, q_y)
        assert isinstance(loss, float)
        assert len(rn.loss_history) == 1

    def test_evaluate_step(self):
        np.random.seed(42)
        rn = RelationNetwork(embedding_dim=16)
        supp_x = np.random.randn(4, 8).astype(np.float64)
        supp_y = np.array([0, 1, 0, 1])
        q_x = np.random.randn(2, 8).astype(np.float64)
        q_y = np.array([0, 1])
        result = rn.evaluate_step(supp_x, supp_y, q_x, q_y)
        assert "accuracy" in result
        assert "predictions" in result

    def test_get_few_shot_report(self):
        rn = RelationNetwork()
        rn.train_step(np.random.randn(4, 8), np.array([0, 1, 0, 1]), np.random.randn(2, 8), np.array([0, 1]))
        report = rn.get_few_shot_report()
        assert "steps" in report
        assert "last_loss" in report
