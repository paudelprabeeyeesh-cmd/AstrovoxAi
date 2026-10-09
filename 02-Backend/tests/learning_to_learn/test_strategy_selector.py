from learning_to_learn.strategy_selector import StrategySelector, Strategy


def test_strategy_creation():
    strategy = Strategy(name="s1", complexity=0.2)
    assert strategy.name == "s1"
    assert strategy.complexity == 0.2
    assert strategy.requirements == []
    assert strategy.expected_performance == 0.5


def test_strategy_selector_register():
    selector = StrategySelector()
    strategy = Strategy(name="s1", complexity=0.2)
    selector.register_strategy(strategy)
    assert "s1" in selector.strategies


def test_strategy_selector_select_no_strategies():
    selector = StrategySelector()
    try:
        selector.select({"f1": 0.5})
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")


def test_strategy_selector_select_best():
    selector = StrategySelector()
    selector.register_strategy(Strategy(name="s1", complexity=0.2, expected_performance=0.4))
    selector.register_strategy(Strategy(name="s2", complexity=0.1, expected_performance=0.8))
    best = selector.select({"f1": 0.5})
    assert best == "s2"


def test_strategy_selector_rank():
    selector = StrategySelector()
    selector.register_strategy(Strategy(name="s1", complexity=0.9, expected_performance=0.3))
    selector.register_strategy(Strategy(name="s2", complexity=0.1, expected_performance=0.8))
    ranked = selector.rank({"f1": 0.5})
    assert ranked[0][0] == "s2"
    assert ranked[1][0] == "s1"


def test_strategy_selector_get_strategy():
    selector = StrategySelector()
    selector.register_strategy(Strategy(name="s1", complexity=0.2))
    assert selector.get_strategy("s1") is not None
    assert selector.get_strategy("missing") is None


def test_strategy_selector_feature_bonus():
    selector = StrategySelector()
    selector.register_strategy(Strategy(name="s1", complexity=0.1, expected_performance=0.5, requirements=["f1"]))
    selector.register_strategy(Strategy(name="s2", complexity=0.1, expected_performance=0.5, requirements=[]))
    best = selector.select({"f1": 0.5})
    assert best == "s1"


def test_strategy_selector_complexity_penalty():
    selector = StrategySelector()
    selector.register_strategy(Strategy(name="s1", complexity=1.0, expected_performance=0.5))
    selector.register_strategy(Strategy(name="s2", complexity=0.0, expected_performance=0.5))
    best = selector.select({"f1": 0.5})
    assert best == "s2"
