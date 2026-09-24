import numpy as np
from alignment.ppo import clipped_surrogate, compute_gae, ppo_loss, value_loss


class TestClippedSurrogate:
    def test_positive_advantage_clipped(self):
        ratio = np.array([1.1, 0.9])
        adv = np.array([1.0, 1.0])
        eps = 0.2
        loss = clipped_surrogate(ratio, adv, eps)
        assert np.all(loss <= 0)

    def test_negative_advantage_clipped(self):
        ratio = np.array([1.1, 0.9])
        adv = np.array([-1.0, -1.0])
        loss = clipped_surrogate(ratio, adv, 0.2)
        assert np.isfinite(loss).all()
        assert np.all(loss >= 0)

    def test_clipping_bounds(self):
        ratio = np.array([1.5, 0.5])
        adv = np.array([1.0, 1.0])
        loss = clipped_surrogate(ratio, adv, 0.2)
        assert np.isfinite(loss).all()


class TestValueLoss:
    def test_zero_when_equal(self):
        pred = np.array([0.5, -0.2])
        target = np.array([0.5, -0.2])
        assert np.isclose(value_loss(pred, target), 0.0)

    def test_mse_property(self):
        pred = np.array([0.0, 1.0])
        target = np.array([1.0, 0.0])
        expected = 1.0
        assert np.isclose(value_loss(pred, target), expected)


class TestGAE:
    def test_advantage_shape(self):
        rewards = np.zeros(10)
        values = np.zeros(11)
        dones = np.zeros(10)
        adv = compute_gae(rewards, values, dones)
        assert adv.shape == (10,)

    def test_done_terminates(self):
        rewards = np.zeros(10)
        values = np.zeros(11)
        dones = np.zeros(10)
        dones[4] = 1.0
        adv = compute_gae(rewards, values, dones)
        assert np.isfinite(adv).all()


class TestPPOLoss:
    def test_output_keys(self):
        out = ppo_loss(
            log_probs_new=np.zeros(4),
            log_probs_old=np.zeros(4),
            advantages=np.ones(4),
            values_pred=np.zeros(4),
            values_target=np.zeros(4),
            log_probs_ref=np.zeros(4),
        )
        assert "total_loss" in out
        assert "policy_loss" in out
        assert "value_loss" in out
        assert "kl_penalty" in out

    def test_kl_included(self):
        out = ppo_loss(
            log_probs_new=np.log(np.array([0.9, 0.1])),
            log_probs_old=np.zeros(2),
            advantages=np.ones(2),
            values_pred=np.zeros(2),
            values_target=np.zeros(2),
            log_probs_ref=np.log(np.array([0.5, 0.5])),
            beta=1.0,
        )
        assert out["kl_penalty"] > 0
