"""Tests for performance profiling utilities."""

from __future__ import annotations

import time

import pytest

from astrovox.profiling import ProfileReport, Profiler, profile_function


def dummy_work():
    time.sleep(0.01)
    return 42


def test_profiler_records_elapsed_time():
    report = ProfileReport()
    profiler = Profiler(report=report)
    with profiler.measure("dummy"):
        pass
    assert len(report.entries) == 1
    assert report.entries[0].name == "dummy"
    assert report.entries[0].elapsed_ms > 0


def test_profile_function_wraps_execution():
    result, report = profile_function(dummy_work)
    assert result == 42
    assert len(report.entries) == 1


def test_profile_report_summary_contains_name():
    report = ProfileReport()
    report.add(type("E", (), {"name": "op", "elapsed_ms": 1.0, "memory_bytes": 0})())
    summary = report.summary()
    assert "op" in summary
    assert "1.000" in summary
