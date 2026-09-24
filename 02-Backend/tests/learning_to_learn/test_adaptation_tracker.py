import math

from learning_to_learn.adaptation_tracker import AdaptationTracker, AdaptationRecord


def test_adaptation_record_creation():
    record = AdaptationRecord(task_id="t1", before_performance=0.5, after_performance=0.7, steps=1)
    assert record.task_id == "t1"
    assert record.before_performance == 0.5
    assert record.after_performance == 0.7
    assert record.steps == 1
    assert record.metadata == {}


def test_adaptation_tracker_record_adaptation():
    tracker = AdaptationTracker()
    record = tracker.record_adaptation("t1", 0.5, 0.7, steps=1)
    assert record.task_id == "t1"
    assert len(tracker.records["t1"]) == 1
    assert tracker.latest_step["t1"] == 0.7


def test_adaptation_tracker_record_adaptation_with_metadata():
    tracker = AdaptationTracker()
    record = tracker.record_adaptation("t1", 0.5, 0.7, steps=2, metadata={"source": "test"})
    assert record.metadata["source"] == "test"
    assert record.steps == 2


def test_adaptation_tracker_record_step_first_time():
    tracker = AdaptationTracker()
    tracker.record_step("t1", 0.5)
    assert tracker.latest_step["t1"] == 0.5
    assert len(tracker.records.get("t1", [])) == 0


def test_adaptation_tracker_record_step_creates_record():
    tracker = AdaptationTracker()
    tracker.record_step("t1", 0.5)
    tracker.record_step("t1", 0.7)
    assert len(tracker.records["t1"]) == 1
    assert tracker.records["t1"][0].after_performance == 0.7


def test_adaptation_tracker_get_adaptation_rate_empty():
    tracker = AdaptationTracker()
    assert tracker.get_adaptation_rate("t1") == 0.0


def test_adaptation_tracker_get_adaptation_rate():
    tracker = AdaptationTracker()
    tracker.record_adaptation("t1", 0.5, 0.7, steps=1)
    tracker.record_adaptation("t1", 0.7, 0.8, steps=1)
    rate = tracker.get_adaptation_rate("t1")
    assert math.isclose(rate, 0.15)


def test_adaptation_tracker_get_convergence_status_insufficient():
    tracker = AdaptationTracker()
    status = tracker.get_convergence_status("t1")
    assert status["converged"] is False
    assert status["reason"] == "insufficient_data"


def test_adaptation_tracker_get_convergence_status_converged():
    tracker = AdaptationTracker()
    tracker.record_adaptation("t1", 0.5, 0.5, steps=1)
    tracker.record_adaptation("t1", 0.5, 0.5, steps=1)
    tracker.record_adaptation("t1", 0.5, 0.5, steps=1)
    status = tracker.get_convergence_status("t1", threshold=0.01)
    assert status["converged"] is True


def test_adaptation_tracker_get_convergence_status_not_converged():
    tracker = AdaptationTracker()
    tracker.record_adaptation("t1", 0.5, 0.7, steps=1)
    tracker.record_adaptation("t1", 0.7, 0.9, steps=1)
    tracker.record_adaptation("t1", 0.9, 1.0, steps=1)
    status = tracker.get_convergence_status("t1", threshold=0.01)
    assert status["converged"] is False


def test_adaptation_tracker_get_stats_empty():
    tracker = AdaptationTracker()
    stats = tracker.get_stats("t1")
    assert stats["num_records"] == 0
    assert stats["adaptation_rate"] == 0.0


def test_adaptation_tracker_get_stats():
    tracker = AdaptationTracker()
    tracker.record_adaptation("t1", 0.5, 0.7, steps=1)
    tracker.record_adaptation("t1", 0.7, 0.9, steps=1)
    stats = tracker.get_stats("t1")
    assert stats["num_records"] == 2
    assert stats["latest_performance"] == 0.9
    assert stats["best_performance"] == 0.9


def test_adaptation_tracker_reset_task():
    tracker = AdaptationTracker()
    tracker.record_adaptation("t1", 0.5, 0.7, steps=1)
    tracker.reset("t1")
    assert "t1" not in tracker.records
    assert "t1" not in tracker.latest_step


def test_adaptation_tracker_reset_all():
    tracker = AdaptationTracker()
    tracker.record_adaptation("t1", 0.5, 0.7, steps=1)
    tracker.record_adaptation("t2", 0.3, 0.6, steps=1)
    tracker.reset()
    assert tracker.records == {}
    assert tracker.latest_step == {}
