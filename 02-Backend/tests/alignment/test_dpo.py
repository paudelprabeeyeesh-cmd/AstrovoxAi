import numpy as np
from alignment.dpo import dpo_loss, dpo_accuracy


class TestDPOLoss:
    def test_zero_loss_when_preferred_aligned(self):
        log_c = np.log(np.array([0.9, 0.1]))
        log_r = np.log(np.array([0.1, 0.9]))
        log_ref_c = np.log(np.array([0.5, 0.5]))
        log_ref_r = np.log(np.array([0.5, 0.5]))
        loss = dpo_loss(log_c, log_r, log_ref_c, log_ref_r, beta=1.0)
        assert np.isfinite(loss).all()

    def test_accuracy_perfect(self):
        log_c = np.log(np.array([0.9, 0.9]))
        log_r = np.log(np.array([0.1, 0.1]))
        log_ref_c = np.log(np.array([0.5, 0.5]))
        log_ref_r = np.log(np.array([0.5, 0.5]))
        acc = dpo_accuracy(log_c, log_r, log_ref_c, log_ref_r, beta=1.0)
        assert np.all(acc)

    def test_beta_scaling(self):
        log_c = np.log(np.array([0.8, 0.2]))
        log_r = np.log(np.array([0.2, 0.8]))
        log_ref_c = np.log(np.array([0.5, 0.5]))
        log_ref_r = np.log(np.array([0.5, 0.5]))
        loss1 = dpo_loss(log_c, log_r, log_ref_c, log_ref_r, beta=0.1)
        loss2 = dpo_loss(log_c, log_r, log_ref_c, log_ref_r, beta=1.0)
        assert np.isfinite(loss1).all() and np.isfinite(loss2).all()
