import numpy as np
from complex_learning.transfer_learning_advanced import AdvancedTransferLearning


class TestAdvancedTransferLearning:
    def test_initialization(self):
        atl = AdvancedTransferLearning(input_dim=16, hidden_dim=32, output_dim=5)
        assert atl.input_dim == 16
        assert atl.frozen_layers == []

    def test_freeze_unfreeze(self):
        atl = AdvancedTransferLearning(input_dim=16)
        atl.freeze_layer("W1")
        assert "W1" in atl.frozen_layers
        atl.unfreeze_layer("W1")
        assert "W1" not in atl.frozen_layers

    def test_load_source_weights(self):
        atl = AdvancedTransferLearning(input_dim=16, hidden_dim=32, output_dim=5)
        src = {
            "W1": np.random.randn(16, 32).astype(np.float64),
            "b1": np.zeros(32, dtype=np.float64),
        }
        atl.load_source_weights(src)
        assert np.allclose(atl.params["W1"], src["W1"])

    def test_fine_tune_step(self):
        atl = AdvancedTransferLearning(input_dim=16, hidden_dim=32, output_dim=5)
        x = np.random.randn(8, 16)
        y = np.random.randint(0, 5, size=8)
        loss = atl.fine_tune_step(x, y, lr=0.01)
        assert isinstance(loss, float)
        assert len(atl.loss_history) == 1

    def test_frozen_layer_no_update(self):
        atl = AdvancedTransferLearning(input_dim=16, hidden_dim=32, output_dim=5)
        atl.freeze_layer("W1")
        w1_before = atl.params["W1"].copy()
        x = np.random.randn(8, 16)
        y = np.random.randint(0, 5, size=8)
        atl.fine_tune_step(x, y, lr=0.01)
        assert np.allclose(atl.params["W1"], w1_before)

    def test_domain_adaptation_step(self):
        atl = AdvancedTransferLearning(input_dim=16, hidden_dim=32, output_dim=5)
        source_x = np.random.randn(8, 16)
        source_y = np.random.randint(0, 5, size=8)
        target_x = np.random.randn(4, 16)
        loss = atl.domain_adaptation_step(source_x, source_y, target_x, lr=0.01)
        assert isinstance(loss, float)

    def test_transfer_task(self):
        atl = AdvancedTransferLearning(input_dim=16, hidden_dim=32, output_dim=5)
        support_x = np.random.randn(8, 16)
        support_y = np.random.randint(0, 5, size=8)
        query_x = np.random.randn(4, 16)
        preds = atl.transfer_task(support_x, support_y, query_x, steps=3)
        assert preds.shape == (4,)

    def test_transfer_report(self):
        atl = AdvancedTransferLearning(input_dim=16)
        report = atl.get_transfer_report()
        assert "frozen_layers" in report
        assert "transfer_accuracy" in report
