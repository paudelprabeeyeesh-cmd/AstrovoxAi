import pytest
from active_learning.query_strategy import QueryStrategy


class TestQueryStrategy:
    def test_all_returns_all_strategies(self):
        strategies = QueryStrategy.all()
        assert len(strategies) == 5
        assert "uncertainty" in strategies
        assert "entropy" in strategies
        assert "margin" in strategies
        assert "random" in strategies
        assert "expected_learning_gain" in strategies

    def test_validate_valid_strategies(self):
        for s in QueryStrategy.all():
            assert QueryStrategy.validate(s) == s

    def test_validate_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            QueryStrategy.validate("unknown_strategy")

    def test_validate_empty_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            QueryStrategy.validate("")
