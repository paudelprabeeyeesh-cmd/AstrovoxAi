from evals.eval_harness import EvalHarness


def test_run_returns_overall():
    harness = EvalHarness()
    result = harness.run("Explain gravity", "Gravity pulls objects toward Earth", "Gravity explanation")
    assert "overall" in result
    assert 0.0 <= result["overall"] <= 1.0


def test_run_scores_all_present():
    harness = EvalHarness()
    result = harness.run("Test prompt", "Test response", "Test reference")
    assert "prompt_scores" in result
    assert "safety_scores" in result
    assert "capability_scores" in result
    assert "prompt_overall" in result
    assert "safety_overall" in result
    assert "capability_overall" in result


def test_report_empty():
    harness = EvalHarness()
    report = harness.report()
    assert report["count"] == 0
    assert report["avg_overall"] == 0.0


def test_report_after_runs():
    harness = EvalHarness()
    harness.run("Prompt one", "Response one", "Reference one")
    harness.run("Prompt two", "Response two", "Reference two")
    report = harness.report()
    assert report["count"] == 2
    assert 0.0 <= report["avg_overall"] <= 1.0
    assert "avg_prompt" in report
    assert "avg_safety" in report
    assert "avg_capability" in report


def test_passed_threshold():
    harness = EvalHarness()
    harness.run("Good prompt", "Good response", "Good reference")
    assert harness.passed(threshold=0.0) is True


def test_failed_threshold():
    harness = EvalHarness()
    harness.run("Bad prompt", "Bad response", "Bad reference")
    # Default threshold is 0.5, but since scores are computed heuristically,
    # we test with a high threshold to ensure False is possible
    assert harness.passed(threshold=2.0) is False
