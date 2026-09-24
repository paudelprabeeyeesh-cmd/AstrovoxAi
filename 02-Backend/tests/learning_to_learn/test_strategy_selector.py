import pytest
from learning_to_learn.strategy_selector import StrategySelector, Strategy


class TestStrategySelector:
    def test_register_and_select(self):
        ss = StrategySelector()
        ss.register_strategy(Strategy(name="fast", complexity=0.2, expected_performance=0.6))
        ss.register_strategy(Strategy(name="accurate", complexity=0.8, expected_performance=0.9))
        choice = ss.select({"feature_a": 1.0})
        assert choice in ("fast", "accurate")

    def test_select_empty_raises(self):
        ss = StrategySelector()
        with pytest.raises(RuntimeError, match="No strategies registered"):
            ss.select({})

    def test_rank_returns_sorted(self):
        ss = StrategySelector()
        ss.register_strategy(Strategy(name="a", complexity=0.5, expected_performance=0.4))
        ss.register_strategy(Strategy(name="b", complexity=0.1, expected_performance=0.9))
        ranked = ss.rank({})
        names = [n for n, _ in ranked]
        assert names == ["b", "a"]

    def test_requirement_bonus(self):
        ss = StrategySelector()
        ss.register_strategy(Strategy(name="req", complexity=0.5, requirements=["feature_a"], expected_performance=0.4))
        ss.register_strategy(Strategy(name="noreq", complexity=0.1, expected_performance=0.4))
        choice = ss.select({"feature_a": 1.0})
        assert choice == "req"

    def test_get_strategy(self):
        ss = StrategySelector()
        s = Strategy(name="s1", complexity=0.3)
        ss.register_strategy(s)
        assert ss.get_strategy("s1") is s
        assert ss.get_strategy("missing") is None
