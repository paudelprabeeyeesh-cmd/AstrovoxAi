
from complex_learning.self_supervised_advanced import AdvancedSelfSupervisedLearner
import numpy as np


class TestAdvancedSelfSupervisedLearner:
    def test_initialization(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        assert ssl.input_dim == 8
        assert ssl.projection_dim == 128
        assert ssl.temperature == 0.07
        assert len(ssl.params) == 4

    def test_relu(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        x = np.array([[-1.0, 0.0, 1.0]])
        assert np.allclose(ssl._relu(x), [[0.0, 0.0, 1.0]])

    def test_softmax(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        x = np.array([[0.0, 1.0, 2.0]])
        probs = ssl._softmax(x)
        assert np.allclose(np.sum(probs, axis=1), 1.0)

    def test_encode(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        z = ssl._encode(x, ssl.params)
        assert z.shape == (4, 128)

    def test_nt_xent_loss(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        z_i = np.random.randn(4, 16).astype(np.float64)
        z_j = np.random.randn(4, 16).astype(np.float64)
        loss = ssl._nt_xent_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_train_step(self):
        np.random.seed(42)
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        x_aug = x + np.random.randn(4, 8).astype(np.float64) * 0.01
        result = ssl.train_step(x, x_aug)
        assert "loss" in result
        assert "temperature" in result
        assert len(ssl.loss_history) == 1

    def test_mask_and_reconstruct(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        masked, target = ssl.mask_and_reconstruct(x, mask_ratio=0.15)
        assert masked.shape == x.shape
        assert target.shape[0] == 4 * int(8 * 0.15)

    def test_contrastive_loss(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        z_i = np.random.randn(4, 16).astype(np.float64)
        z_j = np.random.randn(4, 16).astype(np.float64)
        loss = ssl.contrastive_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_evaluate(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        x_pos = np.random.randn(4, 8).astype(np.float64)
        x_neg = np.random.randn(4, 8).astype(np.float64)
        result = ssl.evaluate(x, x_pos, x_neg)
        assert "triplet_loss" in result

    def test_get_ssl_report(self):
        ssl = AdvancedSelfSupervisedLearner(input_dim=8)
        ssl.train_step(np.random.randn(4, 8), np.random.randn(4, 8))
        report = ssl.get_ssl_report()
        assert "num_steps" in report
        assert "last_loss" in report
