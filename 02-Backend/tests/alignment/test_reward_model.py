import numpy as np
from alignment.reward_model import bradley_terry_loss, compute_rewards


class TestBradleyTerryLoss:
    def test_positive_diff(self):
        r_w = np.array([1.0, 2.0])
        r_l = np.array([0.0, 1.0])
        loss = bradley_terry_loss(r_w, r_l)
        assert np.all(loss > 0)
        assert np.all(np.isfinite(loss))

    def test_negative_diff(self):
        r_w = np.array([0.0, 1.0])
        r_l = np.array([1.0, 2.0])
        loss = bradley_terry_loss(r_w, r_l)
        assert np.all(loss > 0)

    def test_zero_diff(self):
        r_w = np.array([0.0, 0.0])
        r_l = np.array([0.0, 0.0])
        loss = bradley_terry_loss(r_w, r_l)
        expected = -np.log(0.5 + 1e-8)
        assert np.allclose(loss, expected)

    def test_batch_shape(self):
        r_w = np.random.randn(32)
        r_l = np.random.randn(32)
        loss = bradley_terry_loss(r_w, r_l)
        assert loss.shape == (32,)

    def test_compute_rewards_identity(self):
        logits = np.array([0.1, -0.2, 0.5])
        assert np.allclose(compute_rewards(logits), logits)
