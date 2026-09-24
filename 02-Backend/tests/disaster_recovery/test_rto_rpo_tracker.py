import time

from disaster_recovery.rto_rpo_tracker import RtoRpoTracker


def test_event_lifecycle():
    tracker = RtoRpoTracker()
    tracker.start_event("incident-1")
    time.sleep(0.01)
    tracker.record_recovery_point("incident-1", time.time() - 0.005)
    rto = tracker.end_event("incident-1")
    assert rto is not None
    assert rto >= 0.01


def test_rpo_calculation():
    tracker = RtoRpoTracker()
    tracker.start_event("incident-2")
    time.sleep(0.02)
    tracker.record_recovery_point("incident-2", time.time() - 0.01)
    tracker.end_event("incident-2")
    rpo = tracker.get_rpo("incident-2")
    assert rpo is not None
    assert rpo >= 0.005


def test_get_rto_returns_none_before_end():
    tracker = RtoRpoTracker()
    tracker.start_event("incident-3")
    assert tracker.get_rto("incident-3") is None


def test_get_rpo_returns_none_without_points():
    tracker = RtoRpoTracker()
    tracker.start_event("incident-4")
    tracker.end_event("incident-4")
    assert tracker.get_rpo("incident-4") is None


def test_get_metrics():
    tracker = RtoRpoTracker()
    tracker.start_event("incident-5")
    time.sleep(0.01)
    tracker.end_event("incident-5")
    tracker.start_event("incident-6")
    time.sleep(0.01)
    tracker.end_event("incident-6")
    metrics = tracker.get_metrics()
    assert metrics["count"] == 2
    assert metrics["avg_rto"] is not None
    assert metrics["max_rto"] is not None
    assert metrics["avg_rpo"] is None
    assert metrics["max_rpo"] is None


def test_start_event_while_locked():
    tracker = RtoRpoTracker()
    tracker.start_event("incident-7")
    try:
        tracker.start_event("incident-8")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")
