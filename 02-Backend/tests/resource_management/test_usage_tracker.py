import pytest
from resource_management import UsageTracker


def test_record_and_get():
    tracker = UsageTracker()
    tracker.record("user", "cpu", 1.0)
    assert tracker.get("user", "cpu") == 1.0


def test_reset_clears_count():
    tracker = UsageTracker()
    tracker.record("user", "cpu", 2.0)
    tracker.reset("user", "cpu")
    assert tracker.get("user", "cpu") == 0.0


def test_report_contains_data():
    tracker = UsageTracker()
    tracker.record("user", "cpu", 1.0)
    tracker.record("user", "mem", 2.0)
    report = tracker.report()
    assert report["user"]["cpu"] == 1.0
    assert report["user"]["mem"] == 2.0
