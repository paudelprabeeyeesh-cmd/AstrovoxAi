import numpy as np
import pytest
from advanced_learning.contrastive_learning import SimCLR, SimCLRConfig


class TestSimCLR:
    def test_initialization(self):
        config = SimCLRConfig(input_dim=32)
        simclr = SimCLR(config)
        assert simclr.config.input_dim == 32
        assert simclr.config.projection_dim == 128
        assert simclr.config.temperature == 0.07
        assert len(simclr.loss_history) == 0

    def test_project(self):
        config = SimCLRConfig(input_dim=32)
        simclr = SimCLR(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = simclr._project(x)
        assert z.shape == (8, 128)

    def test_nt_xent_loss(self):
        config = SimCLRConfig(input_dim=32, projection_dim=64)
        simclr = SimCLR(config)
        z_i = np.random.randn(8, 64).astype(np.float64)
        z_j = np.random.randn(8, 64).astype(np.float64)
        loss = simclr._nt_xent_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_train_step(self):
        config = SimCLRConfig(input_dim=32)
        simclr = SimCLR(config)
        x_i = np.random.randn(8, 32).astype(np.float64)
        x_j = np.random.randn(8, 32).astype(np.float64)
        result = simclr.train_step(x_i, x_j)
        assert "loss" in result
        assert "temperature" in result
        assert len(simclr.loss_history) == 1

    def test_encode(self):
        config = SimCLRConfig(input_dim=32)
        simclr = SimCLR(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = simclr.encode(x)
        assert z.shape == (8, 128)

    def test_evaluate(self):
        config = SimCLRConfig(input_dim=32, projection_dim=64)
        simclr = SimCLR(config)
        x = np.random.randn(8, 32).astype(np.float64)
        x_pos = np.random.randn(8, 32).astype(np.float64)
        x_neg = np.random.randn(8, 32).astype(np.float64)
        result = simclr.evaluate(x, x_pos, x_neg)
        assert "triplet_loss" in result

    def test_report(self):
        config = SimCLRConfig(input_dim=32)
        simclr = SimCLR(config)
        x_i = np.random.randn(8, 32).astype(np.float64)
        x_j = np.random.randn(8, 32).astype(np.float64)
        simclr.train_step(x_i, x_j)
        report = simclr.get_report()
        assert "num_steps" in report
        assert report["temperature"] == 0.07
