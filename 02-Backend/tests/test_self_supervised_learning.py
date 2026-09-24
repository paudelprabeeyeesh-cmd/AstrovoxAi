import numpy as np
import pytest
from adaptive_learning.self_supervised_learning import SelfSupervisedLearner


class TestSelfSupervisedLearner:
    def test_initialization(self):
        ssl = SelfSupervisedLearner()
        assert ssl.temperature == 0.1
        assert ssl.projection_dim == 128

    def test_project(self):
        ssl = SelfSupervisedLearner()
        x = np.random.randn(10, 8)
        z = ssl._project(x)
        assert z.shape[1] == 128

    def test_nt_xent_loss(self):
        ssl = SelfSupervisedLearner(temperature=0.1)
        z_i = np.random.randn(8, 64)
        z_j = np.random.randn(8, 64)
        loss = ssl.nt_xent_loss(z_i, z_j)
        assert isinstance(loss, float)
        assert loss >= 0.0
        assert len(ssl.loss_history) == 1

    def test_mask_and_reconstruct(self):
        ssl = SelfSupervisedLearner()
        x = np.random.randn(4, 16)
        masked, target = ssl.mask_and_reconstruct(x, mask_ratio=0.25)
        assert masked.shape == x.shape
        assert target.shape[0] == x.shape[0]
        assert target.shape[1] == int(16 * 0.25)

    def test_train_step(self):
        ssl = SelfSupervisedLearner()
        x = np.random.randn(8, 16)
        result = ssl.train_step(x)
        assert "contrastive_loss" in result
        assert result["contrastive_loss"] >= 0.0

    def test_cosine_similarity(self):
        ssl = SelfSupervisedLearner()
        a = np.random.randn(5, 8)
        b = np.random.randn(5, 8)
        sim = ssl._cosine_similarity(a, b)
        assert sim.shape == (5, 5)

    def test_get_ssl_report(self):
        ssl = SelfSupervisedLearner()
        ssl.nt_xent_loss(np.random.randn(8, 64), np.random.randn(8, 64))
        report = ssl.get_ssl_report()
        assert report["num_steps"] == 1
        assert "last_loss" in report
