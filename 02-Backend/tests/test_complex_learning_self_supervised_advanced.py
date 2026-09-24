import numpy as np
import pytest
from complex_learning.self_supervised_advanced import AdvancedSelfSupervisedLearner


class TestAdvancedSelfSupervisedLearner:
    def test_initialization(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        assert assl.input_dim == 32
        assert assl.temperature == 0.07
        assert assl.queue_size == 4096

    def test_encode(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        x = np.random.randn(8, 32)
        z = assl._encode(x, assl.params)
        assert z.shape == (8, 128)

    def test_nt_xent_loss(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        z_i = np.random.randn(8, 128)
        z_j = np.random.randn(8, 128)
        loss = assl._nt_xent_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_mask_and_reconstruct(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        x = np.random.randn(4, 32)
        masked, target = assl.mask_and_reconstruct(x, mask_ratio=0.25)
        assert masked.shape == x.shape
        assert target.shape[0] == x.shape[0]

    def test_train_step(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        x = np.random.randn(8, 32)
        x_aug = np.random.randn(8, 32)
        result = assl.train_step(x, x_aug)
        assert "loss" in result
        assert "temperature" in result
        assert len(assl.loss_history) == 1

    def test_contrastive_loss(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        z_i = np.random.randn(8, 128)
        z_j = np.random.randn(8, 128)
        loss = assl.contrastive_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_evaluate(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        x = np.random.randn(8, 32)
        x_pos = np.random.randn(8, 32)
        x_neg = np.random.randn(8, 32)
        result = assl.evaluate(x, x_pos, x_neg)
        assert "triplet_loss" in result

    def test_ssl_report(self):
        assl = AdvancedSelfSupervisedLearner(input_dim=32, projection_dim=128)
        x = np.random.randn(8, 32)
        x_aug = np.random.randn(8, 32)
        assl.train_step(x, x_aug)
        report = assl.get_ssl_report()
        assert "num_steps" in report
        assert "queue_size" in report
