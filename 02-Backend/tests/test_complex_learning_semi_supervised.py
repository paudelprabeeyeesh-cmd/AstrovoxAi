import numpy as np
import pytest
from complex_learning.semi_supervised import SemiSupervisedLearner


class TestSemiSupervisedLearner:
    def test_initialization(self):
        ssl = SemiSupervisedLearner(input_dim=16, hidden_dim=32, num_classes=3)
        assert ssl.input_dim == 16
        assert "W1" in ssl.params
        assert "W1" in ssl.ema_params

    def test_supervised_train_step(self):
        ssl = SemiSupervisedLearner(input_dim=16, hidden_dim=32, num_classes=3)
        x = np.random.randn(8, 16)
        y = np.random.randint(0, 3, size=8)
        loss = ssl.supervised_train_step(x, y, lr=0.01)
        assert isinstance(loss, float)
        assert len(ssl.loss_history) == 1

    def test_generate_pseudo_labels(self):
        ssl = SemiSupervisedLearner(input_dim=16, hidden_dim=32, num_classes=3)
        ssl.supervised_train_step(np.random.randn(4, 16), np.random.randint(0, 3, size=4), lr=0.01)
        unlabeled = np.random.randn(8, 16)
        x_pseudo, y_pseudo = ssl.generate_pseudo_labels(unlabeled, threshold=0.5)
        if len(x_pseudo) > 0:
            assert x_pseudo.shape[1] == 16

    def test_consistency_loss(self):
        ssl = SemiSupervisedLearner(input_dim=16, hidden_dim=32, num_classes=3)
        x = np.random.randn(4, 16)
        x_aug = np.random.randn(4, 16)
        loss = ssl.consistency_loss(x, x_aug)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_train_step_semi(self):
        ssl = SemiSupervisedLearner(input_dim=16, hidden_dim=32, num_classes=3)
        labeled_x = np.random.randn(8, 16)
        labeled_y = np.random.randint(0, 3, size=8)
        unlabeled_x = np.random.randn(8, 16)
        unlabeled_x_aug = np.random.randn(8, 16)
        result = ssl.train_step_semi(labeled_x, labeled_y, unlabeled_x, unlabeled_x_aug,
                                     lambda_u=0.5, lr=0.01)
        assert "loss" in result
        assert "supervised" in result
        assert "unsupervised" in result

    def test_get_semi_sup_report(self):
        ssl = SemiSupervisedLearner(input_dim=16, hidden_dim=32, num_classes=3)
        labeled_x = np.random.randn(8, 16)
        labeled_y = np.random.randint(0, 3, size=8)
        unlabeled_x = np.random.randn(8, 16)
        unlabeled_x_aug = np.random.randn(8, 16)
        ssl.train_step_semi(labeled_x, labeled_y, unlabeled_x, unlabeled_x_aug, lr=0.01)
        report = ssl.get_semi_sup_report()
        assert "total_steps" in report
        assert "pseudo_label_generations" in report
