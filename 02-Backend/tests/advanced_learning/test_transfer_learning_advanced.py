import numpy as np
from advanced_learning.transfer_learning_advanced import AdvancedTransferLearner, TransferConfig


class TestAdvancedTransferLearner:
    def test_initialization(self):
        config = TransferConfig(input_dim=32, output_dim=4)
        atl = AdvancedTransferLearner(config)
        assert atl.config.input_dim == 32
        assert atl.config.output_dim == 4
        assert atl.config.num_layers == 3
        assert len(atl.transfer_history) == 0

    def test_load_base(self):
        config = TransferConfig(input_dim=32, output_dim=4)
        atl = AdvancedTransferLearner(config)
        state = {f'W{i}': np.random.randn(32, 128).astype(np.float64) for i in range(2)}
        state['b0'] = np.zeros(128, dtype=np.float64)
        state['b1'] = np.zeros(4, dtype=np.float64)
        atl.load_base(state)
        assert len(atl.base_params) == len(state)

    def test_freeze_unfreeze(self):
        config = TransferConfig(input_dim=32, output_dim=4, num_layers=3)
        atl = AdvancedTransferLearner(config)
        atl.freeze_layers([0, 1])
        assert 0 in atl.frozen_layers
        assert 1 in atl.frozen_layers
        atl.unfreeze_layers([0])
        assert 0 not in atl.frozen_layers
        assert 1 in atl.frozen_layers

    def test_transfer(self):
        config = TransferConfig(input_dim=32, output_dim=4)
        atl = AdvancedTransferLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        result = atl.transfer(x, y, steps=5)
        assert isinstance(result, dict)
        assert len(atl.transfer_history) == 5

    def test_evaluate_transfer(self):
        config = TransferConfig(input_dim=32, output_dim=4)
        atl = AdvancedTransferLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        atl.transfer(x, y, steps=3)
        report = atl.evaluate_transfer(x, y)
        assert "transfer_loss" in report
        assert "base_loss" in report
        assert "improvement" in report

    def test_adapt_domain(self):
        config = TransferConfig(input_dim=32, output_dim=4)
        atl = AdvancedTransferLearner(config)
        src = np.random.randn(16, 32).astype(np.float64)
        tgt = np.random.randn(16, 32).astype(np.float64)
        M = atl.adapt_domain(src, tgt, num_components=10)
        assert isinstance(M, np.ndarray)

    def test_unfreeze_schedule(self):
        config = TransferConfig(input_dim=32, output_dim=4, num_layers=3, unfreeze_schedule=[5, 10])
        atl = AdvancedTransferLearner(config)
        assert atl.config.unfreeze_schedule == [5, 10]

    def test_get_transfer_report(self):
        config = TransferConfig(input_dim=32, output_dim=4)
        atl = AdvancedTransferLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        atl.transfer(x, y, steps=3)
        report = atl.get_transfer_report()
        assert "steps" in report
        assert "frozen_layers" in report
