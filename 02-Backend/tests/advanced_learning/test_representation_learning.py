import numpy as np
from advanced_learning.representation_learning import RepresentationLearner, RepConfig


class TestRepresentationLearner:
    def test_initialization(self):
        config = RepConfig(input_dim=32)
        rl = RepresentationLearner(config)
        assert rl.config.input_dim == 32
        assert rl.config.latent_dim == 32
        assert len(rl.loss_history) == 0

    def test_train_step(self):
        config = RepConfig(input_dim=32)
        rl = RepresentationLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        result = rl.train_step(x)
        assert "loss" in result
        assert "reconstruction_error" in result
        assert len(rl.loss_history) == 1

    def test_extract_features(self):
        config = RepConfig(input_dim=32, latent_dim=16)
        rl = RepresentationLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = rl.extract_features(x)
        assert z.shape == (8, 16)

    def test_reduce_dimensions(self):
        config = RepConfig(input_dim=32, latent_dim=16)
        rl = RepresentationLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = rl.reduce_dimensions(x, n_components=8)
        assert z.shape[1] == 8

    def test_reduce_dimensions_noop(self):
        config = RepConfig(input_dim=32, latent_dim=16)
        rl = RepresentationLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = rl.reduce_dimensions(x, n_components=16)
        assert z.shape[1] == 16

    def test_compute_representation_similarity(self):
        config = RepConfig(input_dim=32)
        rl = RepresentationLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        sim = rl.compute_representation_similarity(x)
        assert sim.shape == (8, 8)

    def test_get_report(self):
        config = RepConfig(input_dim=32)
        rl = RepresentationLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        rl.train_step(x)
        report = rl.get_report()
        assert "num_steps" in report
        assert report["latent_dim"] == 32
