import numpy as np
from ..meta_learning import MetaLearning


class TestMetaLearning:
    def test_initialization(self):
        ml = MetaLearning(feature_dim=4, num_strategies=3)
        assert len(ml.strategies) == 3

    def test_add_task(self):
        ml = MetaLearning()
        task = ml.add_task("math", np.array([0.1, 0.2, 0.3, 0.4]))
        assert task.domain == "math"
        assert task.id.startswith("task_")

    def test_select_strategy(self):
        ml = MetaLearning(feature_dim=4)
        ml.add_task("t1", np.array([0.1, 0.2, 0.3, 0.4]))
        strat = ml.select_strategy(np.array([0.1, 0.2, 0.3, 0.4]))
        assert strat.name in ml.strategies

    def test_adapt_strategy(self):
        ml = MetaLearning(feature_dim=4)
        task = ml.add_task("t", np.array([0.1, 0.2, 0.3, 0.4]))
        strat = ml.select_strategy(task.features)
        old_weights = strat.weights.copy()
        ml.adapt_strategy(strat.name, task.features, 0.8)
        assert not np.allclose(strat.weights, old_weights)
        assert len(strat.performance_history) == 1

    def test_rapid_adapt(self):
        ml = MetaLearning(feature_dim=4)
        task = ml.add_task("t", np.array([0.1, 0.2, 0.3, 0.4]))
        result = ml.rapid_adapt(task, episodes=3)
        assert result["episodes"] == 3
        assert "final_reward" in result

    def test_strategy_performance(self):
        ml = MetaLearning()
        perf = ml.get_strategy_performance()
        assert len(perf) == ml.num_strategies
        for v in perf.values():
            assert v == 0.0
