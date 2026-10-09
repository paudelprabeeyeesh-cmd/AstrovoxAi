
from app.evaluation.bias_fairness import BiasFairnessEvaluator


def test_bias_fairness_clean():
    evaluator = BiasFairnessEvaluator()
    result = evaluator.evaluate("The capital of France is Paris.")
    assert result["score"] >= 0.8
    assert result["risk_level"] == "low"


def test_bias_fairness_suspicious():
    evaluator = BiasFairnessEvaluator()
    result = evaluator.evaluate("Women are naturally better at nursing than men.")
    assert result["score"] < 1.0
    assert result["bias_indicators"] >= 1


def test_demographic_parity_fair():
    evaluator = BiasFairnessEvaluator()
    outcomes = {"group_a": [0.8, 0.7, 0.9], "group_b": [0.75, 0.72, 0.78]}
    result = evaluator.demographic_parity(outcomes)
    assert result["fair"] is True


def test_demographic_parity_unfair():
    evaluator = BiasFairnessEvaluator()
    outcomes = {"group_a": [0.9, 0.9, 0.9], "group_b": [0.1, 0.1, 0.1]}
    result = evaluator.demographic_parity(outcomes)
    assert result["fair"] is False
