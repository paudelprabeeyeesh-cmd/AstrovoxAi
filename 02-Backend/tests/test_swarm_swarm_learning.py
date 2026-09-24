import numpy as np
import pytest
from swarm_intelligence.swarm_learning import SwarmLearning


class TestSwarmLearning:
    def test_train_reduces_loss(self):
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, size=(50, 4))
        y = X @ np.array([1.0, -1.0, 0.5, -0.5])
        sl = SwarmLearning(n_nodes=4, input_dim=4, seed=42)
        losses = sl.train(X, y, rounds=5, lr=0.01, epochs=3, alpha=0.5)
        assert losses[0] >= losses[-1] - 1e-6

    def test_predict_shape(self):
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, size=(50, 4))
        y = X @ np.array([1.0, -1.0, 0.5, -0.5])
        sl = SwarmLearning(n_nodes=4, input_dim=4, seed=42)
        sl.train(X, y, rounds=3, lr=0.01, epochs=3, alpha=0.5)
        preds = sl.predict(X[:5])
        assert preds.shape == (5,)
