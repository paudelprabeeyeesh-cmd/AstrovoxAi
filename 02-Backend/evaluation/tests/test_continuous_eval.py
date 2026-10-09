
from app.evaluation.continuous_eval import ContinuousEvaluator


def _eval_fn() -> dict:
    return {"overall": 0.9}


def test_continuous_evaluator_run_once():
    evaluator = ContinuousEvaluator(_eval_fn)
    record = evaluator.run_once()
    assert record["status"] == "passed"
    assert record["details"]["overall"] == 0.9


def test_continuous_evaluator_summary():
    evaluator = ContinuousEvaluator(_eval_fn)
    evaluator.run_once()
    evaluator.run_once()
    summary = evaluator.summary()
    assert summary["count"] == 2
    assert summary["pass_rate"] == 1.0


def test_continuous_evaluator_regression_detection():
    evaluator = ContinuousEvaluator(_eval_fn)
    evaluator.run_once()
    regression = evaluator.detect_regression(baseline_score=0.95, threshold=0.05)
    assert regression is not None
    assert regression["regression"] is True


def test_continuous_evaluator_start_stop():
    evaluator = ContinuousEvaluator(_eval_fn)
    evaluator.start()
    assert evaluator._running is True
    evaluator.stop()
    assert evaluator._running is False
