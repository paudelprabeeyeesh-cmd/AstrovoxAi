"""Tests for research evaluation framework - expanded coverage."""

from __future__ import annotations

import math

import pytest

from astrovox.research import ExperimentHarness, ExperimentResult, acceptance_rate, passes_threshold, relative_latency, summarize


def make_config(name: str):
    return type("C", (), {"name": name, "hypothesis": "", "tags": [], "max_minutes": 5})()


def test_acceptance_rate_with_mixed_results():
    results = [
        ExperimentResult(config=make_config("a"), passed=True),
        ExperimentResult(config=make_config("b"), passed=False),
    ]
    registry = {r.config.name: r for r in results}
    assert acceptance_rate(registry) == 0.5


def test_relative_latency_zero_baseline():
    assert relative_latency(0.0, 1.0) == 0.0


def test_relative_latency_positive():
    assert relative_latency(1.0, 1.1) == pytest.approx(0.1)


def test_passes_threshold_false_when_over_budget():
    assert passes_threshold(0.2, threshold=0.10) is False


def test_summarize_empty_results():
    assert summarize([])["count"] == 0


def test_summarize_counts_passed_and_failed():
    results = [
        ExperimentResult(config=make_config("a"), passed=True),
        ExperimentResult(config=make_config("b"), passed=True),
        ExperimentResult(config=make_config("c"), passed=False),
    ]
    summary = summarize(results)
    assert summary["passed"] == 2
    assert summary["failed"] == 1
    assert summary["acceptance_rate"] == pytest.approx(2 / 3)


def test_experiment_harness_registers_results():
    harness = ExperimentHarness()
    harness.run(make_config("a"), lambda: {"m": 1})
    harness.run(make_config("b"), lambda: {"m": 2})
    assert len(harness.registry) == 2
