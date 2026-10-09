
from complex_learning.transfer_learning_advanced import AdvancedTransferLearning
import numpy as np


class TestAdvancedTransferLearning:
    def test_initialization(self):
        tl = AdvancedTransferLearning(input_dim=8)
        assert tl.input_dim == 8
        assert tl.hidden_dim == 64
        assert tl.output_dim == 5
        assert tl.frozen_layers == []

    def test_forward(self):
        tl = AdvancedTransferLearning(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        h, logits = tl._forward(x)
        assert h.shape == (4, 64)
        assert logits.shape == (4, 5)

    def test_compute_loss(self):
        tl = AdvancedTransferLearning(input_dim=8)
        logits = np.random.randn(4, 5).astype(np.float64)
        y = np.array([0, 1, 2, 3])
        loss = tl._compute_loss(logits, y)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_freeze_unfreeze(self):
        tl = AdvancedTransferLearning(input_dim=8)
        tl.freeze_layer("W1")
        assert "W1" in tl.frozen_layers
        tl.unfreeze_layer("W1")
        assert "W1" not in tl.frozen_layers

    def test_load_source_weights(self):
        tl = AdvancedTransferLearning(input_dim=8)
        np.random.seed(42)
        src = {
            "W1": np.random.randn(8, 64).astype(np.float64),
            "b1": np.zeros(64, dtype=np.float64),
        }
        tl.load_source_weights(src)
        np.testing.assert_array_equal(tl.params["W1"], src["W1"])

    def test_fine_tune_step(self):
        tl = AdvancedTransferLearning(input_dim=8, hidden_dim=16, output_dim=3)
        np.random.seed(42)
        tl.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 16).astype(np.float64) * 0.1,
            "b2": np.zeros(16, dtype=np.float64),
            "W3": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b3": np.zeros(3, dtype=np.float64),
        }
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        loss = tl.fine_tune_step(x, y, lr=0.01)
        assert isinstance(loss, float)
        assert len(tl.loss_history) == 1

    def test_frozen_layer_no_update(self):
        tl = AdvancedTransferLearning(input_dim=8, hidden_dim=16, output_dim=3)
        np.random.seed(42)
        tl.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 16).astype(np.float64) * 0.1,
            "b2": np.zeros(16, dtype=np.float64),
            "W3": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b3": np.zeros(3, dtype=np.float64),
        }
        tl.freeze_layer("W1")
        w1_before = tl.params["W1"].copy()
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        tl.fine_tune_step(x, y, lr=0.1)
        np.testing.assert_array_equal(tl.params["W1"], w1_before)

    def test_mmd_loss(self):
        tl = AdvancedTransferLearning(input_dim=8)
        f_s = np.random.randn(4, 16).astype(np.float64)
        f_t = np.random.randn(4, 16).astype(np.float64)
        mmd = tl._mmd_loss(f_s, f_t)
        assert isinstance(mmd, float)
        assert mmd >= 0.0

    def test_transfer_task(self):
        tl = AdvancedTransferLearning(input_dim=8, hidden_dim=16, output_dim=3)
        np.random.seed(42)
        tl.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 16).astype(np.float64) * 0.1,
            "b2": np.zeros(16, dtype=np.float64),
            "W3": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b3": np.zeros(3, dtype=np.float64),
        }
        supp_x = np.random.randn(6, 8).astype(np.float64)
        supp_y = np.array([0, 1, 2, 0, 1, 2])
        q_x = np.random.randn(3, 8).astype(np.float64)
        preds = tl.transfer_task(supp_x, supp_y, q_x, steps=2)
        assert preds.shape == (3,)
        assert all(p in [0, 1, 2] for p in preds)

    def test_get_transfer_report(self):
        tl = AdvancedTransferLearning(input_dim=8)
        tl.freeze_layer("W1")
        report = tl.get_transfer_report()
        assert "frozen_layers" in report
        assert "total_steps" in report
        assert "last_loss" in report
