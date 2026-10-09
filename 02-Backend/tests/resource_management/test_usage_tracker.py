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


def test_default_amount_is_one():
    tracker = UsageTracker()
    tracker.record("user", "cpu")
    assert tracker.get("user", "cpu") == 1.0


def test_multiple_subjects_and_resources():
    tracker = UsageTracker()
    tracker.record("user1", "cpu", 1.0)
    tracker.record("user1", "mem", 2.0)
    tracker.record("user2", "cpu", 3.0)
    assert tracker.get("user1", "cpu") == 1.0
    assert tracker.get("user1", "mem") == 2.0
    assert tracker.get("user2", "cpu") == 3.0


def test_record_accumulates():
    tracker = UsageTracker()
    tracker.record("user", "cpu", 1.0)
    tracker.record("user", "cpu", 2.0)
    tracker.record("user", "cpu", 3.0)
    assert tracker.get("user", "cpu") == 6.0


def test_get_returns_zero_for_unused():
    tracker = UsageTracker()
    assert tracker.get("user", "cpu") == 0.0
    assert tracker.get("unknown", "disk") == 0.0


def test_report_returns_plain_dicts():
    tracker = UsageTracker()
    tracker.record("user", "cpu", 1.0)
    report = tracker.report()
    assert type(report) is dict
    assert type(report["user"]) is dict
    assert type(report["user"]["cpu"]) is float
