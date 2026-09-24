import pytest
from learning_to_learn.meta_learner import MetaLearner, MetaParameters, Task


class TestMetaLearner:
    def test_register_and_update_task(self):
        ml = MetaLearner()
        task = Task(task_id="t1", features={"x": 1.0})
        ml.register_task(task)
        ml.update_performance("t1", 0.8)
        assert ml.tasks["t1"].performance_history == [0.8]

    def test_update_performance_unknown_task_raises(self):
        ml = MetaLearner()
        with pytest.raises(KeyError, match="not registered"):
            ml.update_performance("missing", 0.5)

    def test_meta_update_adjusts_exploration(self):
        ml = MetaLearner()
        ml.register_task(Task(task_id="t1", features={}))
        ml.update_performance("t1", 0.3)
        params_before = ml.meta_params.exploration_rate
        ml.meta_update()
        assert ml.meta_params.exploration_rate > params_before

    def test_meta_update_decreases_exploration_on_good_performance(self):
        ml = MetaLearner()
        ml.register_task(Task(task_id="t1", features={}))
        ml.update_performance("t1", 0.9)
        params_before = ml.meta_params.exploration_rate
        ml.meta_update()
        assert ml.meta_params.exploration_rate < params_before

    def test_set_components(self):
        ml = MetaLearner()
        from learning_to_learn.strategy_selector import StrategySelector
        from learning_to_learn.transfer_prior import TransferPrior
        from learning_to_learn.adaptation_tracker import AdaptationTracker
        ss = StrategySelector()
        tp = TransferPrior()
        at = AdaptationTracker()
        ml.set_components(strategy_selector=ss, transfer_prior=tp, adaptation_tracker=at)
        assert ml.strategy_selector is ss
        assert ml.transfer_prior is tp
        assert ml.adaptation_tracker is at

    def test_predict_best_strategy_without_selector_raises(self):
        ml = MetaLearner()
        ml.register_task(Task(task_id="t1", features={}))
        with pytest.raises(RuntimeError, match="StrategySelector not attached"):
            ml.predict_best_strategy("t1")

    def test_suggest_prior_without_transfer_returns_none(self):
        ml = MetaLearner()
        ml.register_task(Task(task_id="t1", features={}))
        assert ml.suggest_prior("t1") is None

    def test_get_task_stats(self):
        ml = MetaLearner()
        ml.register_task(Task(task_id="t1", features={}))
        ml.update_performance("t1", 0.7)
        stats = ml.get_task_stats("t1")
        assert stats["avg_performance"] == 0.7
        assert stats["num_updates"] == 1
        assert stats["latest_performance"] == 0.7

    def test_get_task_stats_unknown_raises(self):
        ml = MetaLearner()
        with pytest.raises(KeyError, match="not registered"):
            ml.get_task_stats("missing")

    def test_default_meta_params(self):
        ml = MetaLearner()
        assert ml.meta_params.learning_rate == 0.01
        assert ml.meta_params.momentum == 0.9
