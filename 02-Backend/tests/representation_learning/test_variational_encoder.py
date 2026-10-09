import numpy as np
from representation_learning.variational_encoder import VariationalAutoencoder, VAEConfig


class TestVariationalAutoencoder:
    def test_initialization(self):
        config = VAEConfig(input_dim=32)
        model = VariationalAutoencoder(config)
        assert model.config.input_dim == 32
        assert model.config.latent_dim == 16
        assert model.config.beta == 1.0
        assert len(model.loss_history) == 0

    def test_encode_shape(self):
        config = VAEConfig(input_dim=32, latent_dim=8)
        model = VariationalAutoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        z = model.encode(x)
        assert z.shape == (4, 8)

    def test_reconstruct_shape(self):
        config = VAEConfig(input_dim=32)
        model = VariationalAutoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        x_hat = model.reconstruct(x)
        assert x_hat.shape == x.shape

    def test_train_step_reduces_loss(self):
        np.random.seed(42)
        config = VAEConfig(input_dim=32, beta=0.5)
        model = VariationalAutoencoder(config)
        x = np.random.randn(8, 32).astype(np.float64)
        loss_before = float(np.mean((x - model.reconstruct(x)) ** 2))
        for _ in range(30):
            model.train_step(x, lr=0.01)
        loss_after = float(np.mean((x - model.reconstruct(x)) ** 2))
        assert loss_after <= loss_before

    def test_train_step_records_history(self):
        config = VAEConfig(input_dim=32)
        model = VariationalAutoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        model.train_step(x)
        assert len(model.loss_history) == 1

    def test_train_step_return_keys(self):
        config = VAEConfig(input_dim=32)
        model = VariationalAutoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        result = model.train_step(x)
        assert "loss" in result
        assert "reconstruction_error" in result
        assert "kl_divergence" in result

    def test_reparameterize(self):
        config = VAEConfig(input_dim=32)
        model = VariationalAutoencoder(config)
        mu = np.zeros((4, 16), dtype=np.float64)
        logvar = np.zeros((4, 16), dtype=np.float64)
        z = VariationalAutoencoder.reparameterize(mu, logvar)
        assert z.shape == (4, 16)
        assert np.allclose(z, 0.0, atol=1e-6)

    def test_get_report(self):
        config = VAEConfig(input_dim=32, beta=0.5)
        model = VariationalAutoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        model.train_step(x)
        report = model.get_report()
        assert report["num_steps"] == 1
        assert report["beta"] == 0.5
        assert "last_loss" in report

    def test_beta_scales_kl(self):
        np.random.seed(42)
        x = np.random.randn(8, 32).astype(np.float64)
        config_low = VAEConfig(input_dim=32, beta=0.0)
        model_low = VariationalAutoencoder(config_low)
        for _ in range(10):
            model_low.train_step(x, lr=0.01)

        config_high = VAEConfig(input_dim=32, beta=1.0)
        model_high = VariationalAutoencoder(config_high)
        np.random.seed(42)
        model_high.__init__(config_high)
        for _ in range(10):
            model_high.train_step(x, lr=0.01)

        assert float(np.mean(model_low.loss_history)) <= float(np.mean(model_high.loss_history))
