import numpy as np
import pytest
from adaptive_learning.transfer_learning import TransferLearner


class TestTransferLearner:
    def test_initialization(self):
        tl = TransferLearner()
        assert tl.base_model == {}
        assert len(tl.frozen_layers) == 0

    def test_load_base(self):
        tl = TransferLearner()
        model_state = {"W": np.random.randn(4, 3), "b": np.zeros(3)}
        tl.load_base(model_state)
        assert "W" in tl.base_model
        assert np.allclose(tl.base_model["W"], model_state["W"])

    def test_freeze_unfreeze_layers(self):
        tl = TransferLearner()
        tl.load_base({"W": np.zeros((4, 3)), "b": np.zeros(3)})
        tl.freeze_layers(["W"])
        assert "W" in tl.frozen_layers
        assert "W" not in tl.fine_tuned_layers
        tl.unfreeze_layers(["W"])
        assert "W" not in tl.frozen_layers
        assert "W" in tl.fine_tuned_layers

    def test_transfer(self):
        tl = TransferLearner()
        tl.load_base({"W": np.random.randn(4, 3), "b": np.zeros(3)})
        target_data = {"W": np.random.randn(4, 3)}
        model = tl.transfer(target_data, fine_tune_lr=0.01, steps=5)
        assert "W" in model
        assert len(tl.transfer_history) == 5
        assert tl.transfer_history[-1]["step"] == 4

    def test_adapt_domain(self):
        tl = TransferLearner()
        source = np.random.randn(100, 10)
        target = np.random.randn(100, 10)
        M = tl.adapt_domain(source, target, num_components=5)
        assert M.shape[0] == 5
        assert M.shape[1] == 5

    def test_get_transfer_report(self):
        tl = TransferLearner()
        tl.load_base({"W": np.zeros((4, 3))})
        tl.transfer({"W": np.random.randn(4, 3)}, steps=3)
        report = tl.get_transfer_report()
        assert report["steps"] == 3
        assert "final_loss" in report
        assert "improvement" in report
