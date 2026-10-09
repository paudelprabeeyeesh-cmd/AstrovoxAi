import numpy as np
from alignment.kl_penalty import kl_divergence, kl_penalty


class TestKLDivergence:
    def test_identical_distributions(self):
        log_p = np.log(np.array([0.25, 0.25, 0.25, 0.25]))
        log_q = np.log(np.array([0.25, 0.25, 0.25, 0.25]))
        kl = kl_divergence(log_p, log_q)
        assert np.allclose(kl, 0.0, atol=1e-6)

    def test_non_negative(self):
        log_p = np.log(np.array([0.7, 0.3]))
        log_q = np.log(np.array([0.5, 0.5]))
        kl = kl_divergence(log_p, log_q)
        assert np.all(kl >= -1e-6)

    def test_penalty_scales_with_beta(self):
        log_p = np.log(np.array([0.9, 0.1]))
        log_q = np.log(np.array([0.5, 0.5]))
        p1 = kl_penalty(log_p, log_q, beta=0.1)
        p2 = kl_penalty(log_p, log_q, beta=0.5)
        assert np.isclose(p1 * 5.0, p2)

    def test_batch_shape(self):
        log_p = np.random.randn(16, 4)
        log_q = np.random.randn(16, 4)
        kl = kl_divergence(log_p, log_q)
        assert kl.shape == (16,)
