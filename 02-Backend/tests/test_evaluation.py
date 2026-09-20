import pytest
from app.evaluation import EvaluationSuite


def test_evaluation_suite_run():
    suite = EvaluationSuite()
    suite.register_suite("demo", [
        {"prompt": "Hello", "expected": "Hello", "rubric": {"pass_threshold": 0.5}},
        {"prompt": "Test", "expected": "Testing", "rubric": {"pass_threshold": 0.5}},
    ])
    result = suite.run_suite("demo", lambda p: f"Response to: {p}")
    assert result["suite"] == "demo"
    assert result["total"] == 2
    assert "passed" in result
    assert "failed" in result
    assert "pass_rate" in result
