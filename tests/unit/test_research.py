"""Tests for research evaluation framework."""

from __future__ import annotations

import pytest

from astrovox.research import ExperimentHarness, ExperimentResult, acceptance_rate, passes_threshold, relative_latency, summarize


def test_experiment_harness_runs_function():
    harness = ExperimentHarness()
    result = harness.run(
        config=type("C", (), {"name": "exp1", "hypothesis": "", "tags": [], "max_minutes": 5})(),
        fn=lambda: {"metric": 1.0},
    )
    assert result.passed is True
    assert result.metrics["metric"] == 1.0


def test_experiment_harness_records_failure():
    harness = ExperimentHarness()
    result = harness.run(
        config=type("C", (), {"name": "exp2", "hypothesis": "", "tags": [], "max_minutes": 5})(),
        fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert result.passed is False
    assert "error" in result.metrics


def test_acceptance_rate_zero_when_empty():
    assert acceptance_rate({}) == 0.0


def test_passes_threshold_true_when_within_budget():
    assert passes_threshold(0.05, threshold=0.10) is True


def test_summarize_counts_results():
    results = [
        ExperimentResult(config=type("C", (), {"name": "a"})(), passed=True),
        ExperimentResult(config=type("C", (), {"name": "b"})(), passed=False),
    ]
    summary = summarize(results)
    assert summary["count"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
