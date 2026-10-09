
from complex_learning.semi_supervised import SemiSupervisedLearner
import numpy as np


class TestSemiSupervisedLearner:
    def test_initialization(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        assert ssl.input_dim == 8
        assert ssl.hidden_dim == 64
        assert ssl.num_classes == 5
        assert ssl.ema_decay == 0.999
        assert len(ssl.params) == 4

    def test_relu(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        x = np.array([[-1.0, 0.0, 1.0]])
        assert np.allclose(ssl._relu(x), [[0.0, 0.0, 1.0]])

    def test_softmax(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        x = np.array([[0.0, 1.0, 2.0]])
        probs = ssl._softmax(x)
        assert np.allclose(np.sum(probs, axis=1), 1.0)

    def test_forward(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        logits = ssl._forward(x, ssl.params)
        assert logits.shape == (4, 5)

    def test_compute_loss(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        logits = np.random.randn(4, 5).astype(np.float64)
        y = np.array([0, 1, 2, 3])
        loss = ssl._compute_loss(logits, y)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_ema_update(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        ssl.params["W1"] += 0.1
        ssl._ema_update()
        assert not np.allclose(ssl.ema_params["W1"], ssl.params["W1"] - 0.1)

    def test_supervised_train_step(self):
        np.random.seed(42)
        ssl = SemiSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        loss = ssl.supervised_train_step(x, y, lr=0.01)
        assert isinstance(loss, float)
        assert len(ssl.loss_history) == 1
        assert len(ssl.supervised_losses) == 1

    def test_generate_pseudo_labels(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        x = np.random.randn(8, 8).astype(np.float64)
        x_sel, y_pseudo = ssl.generate_pseudo_labels(x, threshold=0.95)
        assert x_sel.shape[1] == 8
        assert y_pseudo.shape[0] <= 8

    def test_consistency_loss(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        x_aug = x + np.random.randn(4, 8).astype(np.float64) * 0.01
        loss = ssl.consistency_loss(x, x_aug)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_train_step_semi(self):
        np.random.seed(42)
        ssl = SemiSupervisedLearner(input_dim=8)
        lx = np.random.randn(4, 8).astype(np.float64)
        ly = np.array([0, 1, 2, 0])
        ux = np.random.randn(4, 8).astype(np.float64)
        uxa = ux + np.random.randn(4, 8).astype(np.float64) * 0.01
        result = ssl.train_step_semi(lx, ly, ux, uxa, lambda_u=0.5, lr=0.01)
        assert "loss" in result
        assert "supervised" in result
        assert "unsupervised" in result
        assert len(ssl.loss_history) == 1

    def test_get_semi_sup_report(self):
        ssl = SemiSupervisedLearner(input_dim=8)
        ssl.train_step_semi(np.random.randn(4, 8), np.array([0, 1, 2, 0]),
                            np.random.randn(4, 8), np.random.randn(4, 8))
        report = ssl.get_semi_sup_report()
        assert "total_steps" in report
        assert "last_loss" in report
