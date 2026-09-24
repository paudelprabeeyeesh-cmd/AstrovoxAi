import numpy as np
import pytest
from complex_learning.weakly_supervised import WeaklySupervisedLearner


class TestWeaklySupervisedLearner:
    def test_initialization_max(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="max")
        assert wsl.pooling == "max"
        assert len(wsl.params) == 4

    def test_initialization_attention(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="attention")
        assert wsl.pooling == "attention"
        assert "V" in wsl.attention_params

    def test_instance_forward(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2)
        x = np.random.randn(4, 16)
        logits = wsl._instance_forward(x)
        assert logits.shape == (4, 2)

    def test_forward_bag_max(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="max")
        x = np.random.randn(5, 16)
        logits, alpha = wsl.forward_bag(x)
        assert logits.shape == (2,)
        assert alpha is None

    def test_forward_bag_attention(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="attention")
        x = np.random.randn(5, 16)
        logits, alpha = wsl.forward_bag(x)
        assert logits.shape == (2,)
        assert alpha is not None
        assert np.isclose(np.sum(alpha), 1.0)

    def test_train_bag_max(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="max")
        x = np.random.randn(5, 16)
        loss = wsl.train_bag(x, y=1, lr=0.01)
        assert isinstance(loss, float)
        assert len(wsl.loss_history) == 1

    def test_train_bag_attention(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="attention")
        x = np.random.randn(5, 16)
        loss = wsl.train_bag(x, y=0, lr=0.01)
        assert isinstance(loss, float)

    def test_predict_bag(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="max")
        x = np.random.randn(5, 16)
        pred = wsl.predict_bag(x)
        assert pred in {0, 1}

    def test_instance_classify(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2)
        x = np.random.randn(5, 16)
        preds = wsl.instance_classify(x)
        assert preds.shape == (5,)
        assert set(np.unique(preds)).issubset({0, 1})

    def test_mil_report(self):
        wsl = WeaklySupervisedLearner(input_dim=16, hidden_dim=32, num_classes=2, pooling="attention")
        x = np.random.randn(5, 16)
        wsl.train_bag(x, y=1, lr=0.01)
        report = wsl.get_mil_report()
        assert "total_steps" in report
        assert "pooling" in report
