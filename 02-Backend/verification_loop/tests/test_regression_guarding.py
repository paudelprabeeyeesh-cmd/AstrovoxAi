import numpy as np
from verification_loop.regression_guarding import Edit, RegressionGuard, RegressionResult


def test_regression_guard_passes_when_improved():
    guard = RegressionGuard(threshold=0.0)
    edit = Edit(file_path="a.py", old_text="x", new_text="y", line_start=1, line_end=1)
    result = guard.check(
        edit=edit,
        before_fn=lambda: 0.5,
        after_fn=lambda: 0.8,
    )
    assert result.passed
    assert not result.regression
    assert round(result.delta, 2) == 0.3


def test_regression_guard_flags_regression():
    guard = RegressionGuard(threshold=0.0)
    edit = Edit(file_path="a.py", old_text="x", new_text="y", line_start=1, line_end=1)
    result = guard.check(
        edit=edit,
        before_fn=lambda: 0.9,
        after_fn=lambda: 0.4,
    )
    assert not result.passed
    assert result.regression
    assert result.delta == -0.5


def test_regression_guard_tolerates_within_threshold():
    guard = RegressionGuard(threshold=-0.05)
    edit = Edit(file_path="a.py", old_text="x", new_text="y", line_start=1, line_end=1)
    result = guard.check(
        edit=edit,
        before_fn=lambda: 1.0,
        after_fn=lambda: 0.97,
    )
    assert result.passed
    assert not result.regression
    assert round(result.delta, 2) == -0.03


def test_batch_check_returns_aggregate_metrics():
    guard = RegressionGuard(threshold=0.0)
    edits = [
        Edit(file_path="a.py", old_text="x", new_text="y", line_start=1, line_end=1),
        Edit(file_path="b.py", old_text="p", new_text="q", line_start=5, line_end=5),
    ]
    def before_fn(e):
        return 0.5 if e.file_path == "a.py" else 0.9
    def after_fn(e):
        return 0.8 if e.file_path == "a.py" else 0.4
    report = guard.batch_check(edits, before_fn, after_fn)
    assert report["total_edits"] == 2
    assert report["passed"] == 1
    assert report["failed"] == 1
    assert isinstance(report["mean_delta"], float)
    assert "results" in report
    assert report["results"][0]["file"] == "a.py"


def test_regression_result_contains_edit_details():
    guard = RegressionGuard()
    edit = Edit(file_path="m.py", old_text="a", new_text="b", line_start=10, line_end=12)
    result = guard.check(edit=edit, before_fn=lambda: 1.0, after_fn=lambda: 0.5)
    assert result.details["file"] == "m.py"
    assert result.details["lines"] == "10-12"
    assert result.edit == edit
