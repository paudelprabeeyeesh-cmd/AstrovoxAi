"""Tests for profiling - expanded coverage."""

from __future__ import annotations

import time

import pytest

from astrovox.profiling import ProfileReport, Profiler, profile_function


def test_profiler_multiple_entries():
    report = ProfileReport()
    profiler = Profiler(report=report)
    with profiler.measure("op1"):
        time.sleep(0.001)
    with profiler.measure("op2"):
        time.sleep(0.001)
    assert len(report.entries) == 2
    names = [e.name for e in report.entries]
    assert names == ["op1", "op2"]


def test_profile_report_summary_multiple_entries():
    report = ProfileReport()
    report.add(type("E", (), {"name": "a", "elapsed_ms": 1.0, "memory_bytes": 100})())
    report.add(type("E", (), {"name": "b", "elapsed_ms": 2.0, "memory_bytes": 200})())
    summary = report.summary()
    assert "a" in summary
    assert "b" in summary
