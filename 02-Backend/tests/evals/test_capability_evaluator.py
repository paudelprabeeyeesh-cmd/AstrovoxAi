from evals.capability_evaluator import CapabilityEvaluator


def test_evaluate_returns_scores():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("math", "42", "42")
    assert "task_type" in result
    assert "scores" in result
    assert "overall" in result
    assert set(result["scores"].keys()) == {"fluency", "relevance", "factuality"}


def test_fluency_empty():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("lang", "", "reference")
    assert result["scores"]["fluency"] == 0.0


def test_fluency_ideal():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("lang", "The quick brown fox jumps.", "reference")
    assert result["scores"]["fluency"] == 1.0


def test_relevance_perfect():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("qa", "Paris is the capital of France", "Paris capital France")
    assert result["scores"]["relevance"] == 1.0


def test_relevance_none():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("qa", "Banana bread recipe", "Paris capital France")
    assert result["scores"]["relevance"] == 0.0


def test_factuality_perfect():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("math", "42", "42")
    assert result["scores"]["factuality"] == 1.0


def test_factuality_empty_reference():
    evaluator = CapabilityEvaluator()
    result = evaluator.evaluate("math", "42", "")
    assert result["scores"]["factuality"] == 1.0


def test_aggregate():
    evaluator = CapabilityEvaluator()
    evaluator.evaluate("math", "42", "42")
    evaluator.evaluate("lang", "Hello", "Hello world")
    agg = evaluator.aggregate()
    assert agg["count"] == 2
    assert "avg_overall" in agg
    assert 0.0 <= agg["avg_overall"] <= 1.0


def test_aggregate_empty():
    evaluator = CapabilityEvaluator()
    agg = evaluator.aggregate()
    assert agg["count"] == 0
    assert agg["avg_overall"] == 0.0
