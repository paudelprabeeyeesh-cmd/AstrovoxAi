import pytest
from complex_learning.transfer_learner import TransferLearner


class TestTransferLearner:
    def test_initialization(self):
        tl = TransferLearner(input_dim=4, output_dim=2)
        assert tl.input_dim == 4
        assert tl.output_dim == 2
        assert tl.source_accuracy is None
        assert tl.target_accuracy is None

    def test_add_module(self):
        tl = TransferLearner(input_dim=4, output_dim=2)
        tl.add_module("encoder", params={"W1": [0.1, 0.2]}, source_domain="vision")
        assert "encoder" in tl.modules
        assert tl.modules["encoder"].source_domain == "vision"

    def test_freeze_unfreeze(self):
        tl = TransferLearner(input_dim=4, output_dim=2)
        tl.add_module("encoder")
        tl.freeze_module("encoder")
        assert tl.modules["encoder"].frozen is True
        tl.unfreeze_module("encoder")
        assert tl.modules["encoder"].frozen is False

    def test_freeze_unknown_module(self):
        tl = TransferLearner(input_dim=4, output_dim=2)
        with pytest.raises(KeyError):
            tl.freeze_module("unknown")

    def test_load_source_weights(self):
        tl = TransferLearner(input_dim=4, output_dim=2)
        tl.add_module("encoder")
        tl.load_source_weights("encoder", {"W": [1.0, 2.0]})
        assert tl.modules["encoder"].params["W"] == [1.0, 2.0]

    def test_adapt_to_target(self):
        tl = TransferLearner(input_dim=2, output_dim=2)
        tl.add_module("base")
        x = [[1.0, 2.0], [3.0, 4.0]]
        y = [0, 1]
        loss = tl.adapt_to_target(x, y)
        assert isinstance(loss, float)
        assert tl.target_accuracy is not None

    def test_adapt_mismatched_lengths(self):
        tl = TransferLearner(input_dim=2, output_dim=2)
        tl.add_module("base")
        with pytest.raises(ValueError):
            tl.adapt_to_target([[1.0]], [])

    def test_adapt_no_modules(self):
        tl = TransferLearner(input_dim=2, output_dim=2)
        with pytest.raises(RuntimeError):
            tl.adapt_to_target([[1.0]], [0])

    def test_evaluate_source(self):
        tl = TransferLearner(input_dim=2, output_dim=2)
        x = [[1.0, 2.0], [3.0, 4.0]]
        y = [0, 1]
        loss = tl.evaluate_source(x, y)
        assert isinstance(loss, float)
        assert tl.source_accuracy is not None

    def test_summary(self):
        tl = TransferLearner(input_dim=4, output_dim=2)
        tl.add_module("a")
        tl.add_module("b")
        summary = tl.summary()
        assert summary["modules"] == ["a", "b"]
