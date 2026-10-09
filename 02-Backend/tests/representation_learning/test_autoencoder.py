import numpy as np
from representation_learning.autoencoder import Autoencoder, AutoencoderConfig


class TestAutoencoder:
    def test_initialization(self):
        config = AutoencoderConfig(input_dim=32)
        model = Autoencoder(config)
        assert model.config.input_dim == 32
        assert model.config.latent_dim == 16
        assert len(model.loss_history) == 0

    def test_encode_shape(self):
        config = AutoencoderConfig(input_dim=32, latent_dim=8)
        model = Autoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        z = model.encode(x)
        assert z.shape == (4, 8)

    def test_decode_shape(self):
        config = AutoencoderConfig(input_dim=32, latent_dim=8)
        model = Autoencoder(config)
        z = np.random.randn(4, 8).astype(np.float64)
        x_hat = model.decode(z)
        assert x_hat.shape == (4, 32)

    def test_reconstruct_shape(self):
        config = AutoencoderConfig(input_dim=32)
        model = Autoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        x_hat = model.reconstruct(x)
        assert x_hat.shape == x.shape

    def test_train_step_reduces_loss(self):
        np.random.seed(42)
        config = AutoencoderConfig(input_dim=32)
        model = Autoencoder(config)
        x = np.random.randn(8, 32).astype(np.float64)
        loss_before = float(np.mean((x - model.reconstruct(x)) ** 2))
        for _ in range(20):
            model.train_step(x, lr=0.05)
        loss_after = float(np.mean((x - model.reconstruct(x)) ** 2))
        assert loss_after <= loss_before

    def test_train_step_records_history(self):
        config = AutoencoderConfig(input_dim=32)
        model = Autoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        model.train_step(x)
        assert len(model.loss_history) == 1

    def test_get_report(self):
        config = AutoencoderConfig(input_dim=32)
        model = Autoencoder(config)
        x = np.random.randn(4, 32).astype(np.float64)
        model.train_step(x)
        report = model.get_report()
        assert report["num_steps"] == 1
        assert report["input_dim"] == 32
        assert "last_loss" in report

    def test_tanh_activation(self):
        config = AutoencoderConfig(input_dim=16, activation="tanh")
        model = Autoencoder(config)
        x = np.random.randn(4, 16).astype(np.float64)
        z = model.encode(x)
        x_hat = model.reconstruct(x)
        assert z.shape[1] == 16
        assert x_hat.shape == x.shape

    def test_unsupported_activation_raises(self):
        config = AutoencoderConfig(input_dim=16, activation="leaky_relu")
        model = Autoencoder(config)
        x = np.random.randn(2, 16).astype(np.float64)
        with np.testing.assert_raises(ValueError):
            model.encode(x)
