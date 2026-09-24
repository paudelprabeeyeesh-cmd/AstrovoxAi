import pytest
from learning_to_learn.transfer_prior import TransferPrior


class TestTransferPrior:
    def test_register_and_suggest(self):
        tp = TransferPrior()
        tp.register_prior("t1", {"w": 0.5, "b": 0.1}, confidence=0.9)
        suggestion = tp.suggest({"w": 0.6, "b": 0.2})
        assert suggestion is not None
        assert "w" in suggestion
        assert "b" in suggestion

    def test_suggest_no_match_returns_none(self):
        tp = TransferPrior()
        tp.register_prior("t1", {"w": 0.5})
        suggestion = tp.suggest({"z": 0.5})
        assert suggestion is None

    def test_transfer(self):
        tp = TransferPrior()
        tp.register_prior("t1", {"w": 1.0, "b": 0.5})
        transferred = tp.transfer("t1", "t2", similarity=0.8)
        assert abs(transferred["w"] - 0.8) < 1e-9
        assert abs(transferred["b"] - 0.4) < 1e-9

    def test_transfer_unknown_source_raises(self):
        tp = TransferPrior()
        with pytest.raises(KeyError, match="not found"):
            tp.transfer("missing", "t2", 0.5)

    def test_decay(self):
        tp = TransferPrior()
        tp.register_prior("t1", {"w": 1.0}, confidence=0.8)
        tp.decay("t1", 0.5)
        assert tp.get_confidence("t1") == 0.4
        assert tp.priors["t1"].parameters["w"] == 0.5

    def test_decay_unknown_raises(self):
        tp = TransferPrior()
        with pytest.raises(KeyError, match="not found"):
            tp.decay("missing", 0.5)

    def test_get_confidence(self):
        tp = TransferPrior()
        tp.register_prior("t1", {}, confidence=0.7)
        assert tp.get_confidence("t1") == 0.7

    def test_suggest_returns_none_when_similarity_low(self):
        tp = TransferPrior()
        tp.register_prior("t1", {"w": 0.0})
        suggestion = tp.suggest({"w": 10.0})
        assert suggestion is None
