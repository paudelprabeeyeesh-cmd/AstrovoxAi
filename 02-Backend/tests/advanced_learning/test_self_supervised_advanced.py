import numpy as np
import pytest
from advanced_learning.self_supervised_advanced import AdvancedSelfSupervisedLearner, SSLConfig


class TestAdvancedSelfSupervisedLearner:
    def test_initialization(self):
        config = SSLConfig(input_dim=32)
        assl = AdvancedSelfSupervisedLearner(config)
        assert assl.config.input_dim == 32
        assert assl.config.projection_dim == 128
        assert assl.config.temperature == 0.07
        assert assl.config.queue_size == 4096
        assert len(assl.loss_history) == 0

    def test_encode(self):
        config = SSLConfig(input_dim=32)
        assl = AdvancedSelfSupervisedLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        z = assl._encode(x, assl.params)
        assert z.shape == (8, 128)

    def test_nt_xent_loss(self):
        config = SSLConfig(input_dim=32, projection_dim=64)
        assl = AdvancedSelfSupervisedLearner(config)
        z_i = np.random.randn(8, 64).astype(np.float64)
        z_j = np.random.randn(8, 64).astype(np.float64)
        loss = assl._nt_xent_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_mask_and_reconstruct(self):
        config = SSLConfig(input_dim=32)
        assl = AdvancedSelfSupervisedLearner(config)
        x = np.random.randn(4, 32).astype(np.float64)
        masked, target = assl.mask_and_reconstruct(x, mask_ratio=0.25)
        assert masked.shape == x.shape
        assert target.shape[0] == x.shape[0]

    def test_train_step(self):
        config = SSLConfig(input_dim=32, queue_size=16)
        assl = AdvancedSelfSupervisedLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        result = assl.train_step(x)
        assert "loss" in result
        assert "temperature" in result
        assert len(assl.loss_history) == 1

    def test_contrastive_loss(self):
        config = SSLConfig(input_dim=32, projection_dim=64)
        assl = AdvancedSelfSupervisedLearner(config)
        z_i = np.random.randn(8, 64).astype(np.float64)
        z_j = np.random.randn(8, 64).astype(np.float64)
        loss = assl.contrastive_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_evaluate(self):
        config = SSLConfig(input_dim=32, projection_dim=64)
        assl = AdvancedSelfSupervisedLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        x_pos = np.random.randn(8, 32).astype(np.float64)
        x_neg = np.random.randn(8, 32).astype(np.float64)
        result = assl.evaluate(x, x_pos, x_neg)
        assert "triplet_loss" in result

    def test_ssl_report(self):
        config = SSLConfig(input_dim=32, queue_size=16)
        assl = AdvancedSelfSupervisedLearner(config)
        x = np.random.randn(8, 32).astype(np.float64)
        assl.train_step(x)
        report = assl.get_ssl_report()
        assert "num_steps" in report
        assert "queue_size" in report
        assert "momentum" in report
