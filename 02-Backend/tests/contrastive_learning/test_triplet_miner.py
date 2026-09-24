import numpy as np
import pytest
from contrastive_learning.triplet_miner import TripletMiner


class TestTripletMiner:
    def test_initialization(self):
        miner = TripletMiner(margin=0.3)
        assert miner.margin == pytest.approx(0.3)

    def test_invalid_margin(self):
        with pytest.raises(ValueError):
            TripletMiner(margin=0.0)
        with pytest.raises(ValueError):
            TripletMiner(margin=-1.0)

    def test_mine_random(self):
        miner = TripletMiner(margin=0.2)
        embeddings = np.random.randn(12, 8).astype(np.float64)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        a, p, n = miner.mine_random(embeddings, labels, num_triplets=4)
        assert len(a) == 4
        assert len(p) == 4
        assert len(n) == 4
        for i in range(4):
            assert labels[a[i]] == labels[p[i]]
            assert labels[a[i]] != labels[n[i]]

    def test_mine_random_no_valid(self):
        miner = TripletMiner(margin=0.2)
        embeddings = np.random.randn(3, 4).astype(np.float64)
        labels = np.array([0, 0, 0])
        a, p, n = miner.mine_random(embeddings, labels, num_triplets=4)
        assert len(a) == 0

    def test_mine_hard(self):
        miner = TripletMiner(margin=0.2)
        embeddings = np.random.randn(12, 8).astype(np.float64)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        mined = miner.mine_hard(embeddings, labels, num_triplets=4)
        a, p, n = mined["anchors"], mined["positives"], mined["negatives"]
        assert len(a) <= 4
        if len(a) > 0:
            assert all(labels[a[i]] == labels[p[i]] for i in range(len(a)))
            assert all(labels[a[i]] != labels[n[i]] for i in range(len(a)))

    def test_mine_semi_hard(self):
        miner = TripletMiner(margin=0.2)
        embeddings = np.random.randn(12, 8).astype(np.float64)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        mined = miner.mine_semi_hard(embeddings, labels, num_triplets=4)
        a, p, n = mined["anchors"], mined["positives"], mined["negatives"]
        assert len(a) <= 4

    def test_mine_strategy_random(self):
        miner = TripletMiner()
        embeddings = np.random.randn(12, 8).astype(np.float64)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        result = miner.mine(embeddings, labels, strategy="random", num_triplets=4)
        assert "anchors" in result and "positives" in result and "negatives" in result

    def test_mine_strategy_hard(self):
        miner = TripletMiner()
        embeddings = np.random.randn(12, 8).astype(np.float64)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        result = miner.mine(embeddings, labels, strategy="hard", num_triplets=4)
        assert "anchors" in result

    def test_mine_strategy_semi_hard(self):
        miner = TripletMiner()
        embeddings = np.random.randn(12, 8).astype(np.float64)
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        result = miner.mine(embeddings, labels, strategy="semi_hard", num_triplets=4)
        assert "anchors" in result

    def test_mine_unknown_strategy(self):
        miner = TripletMiner()
        embeddings = np.random.randn(8, 4).astype(np.float64)
        labels = np.array([0, 0, 1, 1, 2, 2, 3, 3])
        with pytest.raises(ValueError, match="Unknown strategy"):
            miner.mine(embeddings, labels, strategy="unknown")

    def test_compute_triplet_loss_empty(self):
        miner = TripletMiner()
        embeddings = np.random.randn(8, 4).astype(np.float64)
        loss = miner.compute_triplet_loss(embeddings, np.array([], dtype=np.int64), np.array([], dtype=np.int64), np.array([], dtype=np.int64))
        assert loss == 0.0

    def test_compute_triplet_loss(self):
        miner = TripletMiner(margin=0.5)
        embeddings = np.random.randn(8, 4).astype(np.float64)
        a = np.array([0, 1])
        p = np.array([2, 3])
        n = np.array([4, 5])
        loss = miner.compute_triplet_loss(embeddings, a, p, n)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_pairwise_distances_symmetry(self):
        miner = TripletMiner()
        embeddings = np.random.randn(6, 4).astype(np.float64)
        dists = miner._pairwise_distances(embeddings)
        assert dists.shape == (6, 6)
        np.testing.assert_allclose(dists, dists.T)
        np.testing.assert_allclose(np.diag(dists), 0.0, atol=1e-12)

    def test_mine_hard_no_valid(self):
        miner = TripletMiner(margin=0.2)
        embeddings = np.random.randn(4, 4).astype(np.float64)
        labels = np.array([0, 0, 0, 0])
        mined = miner.mine_hard(embeddings, labels, num_triplets=4)
        assert len(mined["anchors"]) == 0

    def test_mine_semi_hard_no_valid(self):
        miner = TripletMiner(margin=0.2)
        embeddings = np.random.randn(4, 4).astype(np.float64)
        labels = np.array([0, 0, 0, 0])
        mined = miner.mine_semi_hard(embeddings, labels, num_triplets=4)
        assert len(mined["anchors"]) == 0
