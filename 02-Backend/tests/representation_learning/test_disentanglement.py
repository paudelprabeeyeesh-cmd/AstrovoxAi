import numpy as np
from representation_learning.disentanglement import DisentanglementMetrics, DisentanglementConfig


class TestDisentanglementMetrics:
    def test_initialization(self):
        config = DisentanglementConfig(latent_dim=8)
        dm = DisentanglementMetrics(config)
        assert dm.config.latent_dim == 8
        assert dm.config.n_factors == 5

    def test_beta_vae_score(self):
        np.random.seed(42)
        config = DisentanglementConfig(latent_dim=4, n_factors=2)
        dm = DisentanglementMetrics(config)
        n = 60
        z = np.random.randn(n, 4).astype(np.float64)
        factors = np.zeros((n, 2), dtype=np.float64)
        factors[:30, 0] = 0
        factors[30:, 0] = 1
        factors[:20, 1] = 0
        factors[20:40, 1] = 1
        factors[40:, 1] = 2
        score = dm.beta_vae_score(z, factors)
        assert isinstance(score, float)
        assert score >= 0.0

    def test_factor_vae_score(self):
        np.random.seed(42)
        config = DisentanglementConfig(latent_dim=4, n_factors=2)
        dm = DisentanglementMetrics(config)
        n = 60
        z = np.random.randn(n, 4).astype(np.float64)
        factors = np.zeros((n, 2), dtype=np.float64)
        factors[:30, 0] = 0
        factors[30:, 0] = 1
        factors[:20, 1] = 0
        factors[20:40, 1] = 1
        factors[40:, 1] = 2
        score = dm.factor_vae_score(z, factors)
        assert isinstance(score, float)
        assert score >= 0.0
        assert score <= 1.0

    def test_mig(self):
        np.random.seed(42)
        config = DisentanglementConfig(latent_dim=4, n_factors=2)
        dm = DisentanglementMetrics(config)
        n = 60
        z = np.random.randn(n, 4).astype(np.float64)
        factors = np.zeros((n, 2), dtype=np.float64)
        factors[:30, 0] = 0
        factors[30:, 0] = 1
        factors[:20, 1] = 0
        factors[20:40, 1] = 1
        factors[40:, 1] = 2
        mig = dm.mutual_information_gap(z, factors)
        assert isinstance(mig, float)
        assert mig >= 0.0

    def test_evaluate_returns_all_metrics(self):
        np.random.seed(42)
        config = DisentanglementConfig(latent_dim=4, n_factors=2)
        dm = DisentanglementMetrics(config)
        n = 60
        z = np.random.randn(n, 4).astype(np.float64)
        factors = np.zeros((n, 2), dtype=np.float64)
        factors[:30, 0] = 0
        factors[30:, 0] = 1
        factors[:20, 1] = 0
        factors[20:40, 1] = 1
        factors[40:, 1] = 2
        result = dm.evaluate(z, factors)
        assert "beta_vae_score" in result
        assert "factor_vae_score" in result
        assert "mig" in result

    def test_mismatched_lengths_raises(self):
        config = DisentanglementConfig(latent_dim=4)
        dm = DisentanglementMetrics(config)
        z = np.random.randn(10, 4).astype(np.float64)
        factors = np.random.randn(5, 2).astype(np.float64)
        with np.testing.assert_raises(ValueError):
            dm.beta_vae_score(z, factors)

    def test_get_report(self):
        config = DisentanglementConfig(latent_dim=8, n_factors=3, n_samples_per_factor=50)
        dm = DisentanglementMetrics(config)
        report = dm.get_report()
        assert report["latent_dim"] == 8
        assert report["n_factors"] == 3
        assert report["n_samples_per_factor"] == 50
