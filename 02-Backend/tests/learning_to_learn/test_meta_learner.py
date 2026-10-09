from learning_to_learn.meta_learner import MetaLearner, MetaParameters, Task


def test_task_creation():
    task = Task(task_id="t1", features={"f1": 0.5})
    assert task.task_id == "t1"
    assert task.features == {"f1": 0.5}
    assert task.performance_history == []


def test_meta_parameters_defaults():
    params = MetaParameters()
    assert params.learning_rate == 0.01
    assert params.momentum == 0.9
    assert params.exploration_rate == 0.1
    assert params.task_similarity_threshold == 0.7
    assert params.adaptation_memory == {}


def test_meta_learner_register_task():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    assert "t1" in learner.tasks


def test_meta_learner_update_performance():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    learner.update_performance("t1", 0.8)
    assert learner.tasks["t1"].performance_history == [0.8]


def test_meta_learner_update_performance_missing_task():
    learner = MetaLearner()
    try:
        learner.update_performance("missing", 0.8)
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")


def test_meta_learner_set_components():
    learner = MetaLearner()
    from learning_to_learn.strategy_selector import StrategySelector
    from learning_to_learn.transfer_prior import TransferPrior
    from learning_to_learn.adaptation_tracker import AdaptationTracker
    learner.set_components(
        strategy_selector=StrategySelector(),
        transfer_prior=TransferPrior(),
        adaptation_tracker=AdaptationTracker(),
    )
    assert learner.strategy_selector is not None
    assert learner.transfer_prior is not None
    assert learner.adaptation_tracker is not None


def test_meta_learner_meta_update_increases_exploration():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    learner.update_performance("t1", 0.2)
    params = learner.meta_update()
    assert params.exploration_rate > 0.1


def test_meta_learner_meta_update_decreases_exploration():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    learner.update_performance("t1", 0.9)
    params = learner.meta_update()
    assert params.exploration_rate < 0.1


def test_meta_learner_meta_update_no_tasks():
    learner = MetaLearner()
    params = learner.meta_update()
    assert params.adaptation_memory == {}


def test_meta_learner_predict_best_strategy_no_selector():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    try:
        learner.predict_best_strategy("t1")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")


def test_meta_learner_predict_best_strategy_missing_task():
    learner = MetaLearner()
    from learning_to_learn.strategy_selector import StrategySelector
    learner.set_components(strategy_selector=StrategySelector())
    try:
        learner.predict_best_strategy("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")


def test_meta_learner_predict_best_strategy():
    learner = MetaLearner()
    from learning_to_learn.strategy_selector import StrategySelector, Strategy
    selector = StrategySelector()
    selector.register_strategy(Strategy(name="s1", complexity=0.1, expected_performance=0.8))
    learner.set_components(strategy_selector=selector)
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    assert learner.predict_best_strategy("t1") == "s1"


def test_meta_learner_suggest_prior_no_transfer():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    assert learner.suggest_prior("t1") is None


def test_meta_learner_suggest_prior_missing_task():
    learner = MetaLearner()
    from learning_to_learn.transfer_prior import TransferPrior
    learner.set_components(transfer_prior=TransferPrior())
    assert learner.suggest_prior("missing") is None


def test_meta_learner_get_task_stats_empty():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    stats = learner.get_task_stats("t1")
    assert stats == {"task_id": "t1", "avg_performance": 0.0, "num_updates": 0}


def test_meta_learner_get_task_stats():
    learner = MetaLearner()
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    learner.update_performance("t1", 0.7)
    learner.update_performance("t1", 0.8)
    stats = learner.get_task_stats("t1")
    assert stats["avg_performance"] == 0.75
    assert stats["num_updates"] == 2
    assert stats["latest_performance"] == 0.8


def test_meta_learner_get_task_stats_missing():
    learner = MetaLearner()
    try:
        learner.get_task_stats("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")


def test_meta_learner_adaptation_tracker_records_steps():
    learner = MetaLearner()
    from learning_to_learn.adaptation_tracker import AdaptationTracker
    tracker = AdaptationTracker()
    learner.set_components(adaptation_tracker=tracker)
    task = Task(task_id="t1", features={"f1": 0.5})
    learner.register_task(task)
    learner.update_performance("t1", 0.6)
    learner.update_performance("t1", 0.7)
    stats = tracker.get_stats("t1")
    assert stats["num_records"] == 1
    assert stats["adaptation_rate"] > 0.0
