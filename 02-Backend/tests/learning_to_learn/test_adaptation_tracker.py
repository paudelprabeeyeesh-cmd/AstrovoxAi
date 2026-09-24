import pytest
from learning_to_learn.adaptation_tracker import AdaptationTracker, AdaptationRecord


class TestAdaptationTracker:
    def test_record_adaptation(self):
        at = AdaptationTracker()
        record = at.record_adaptation("t1", 0.3, 0.6, steps=5)
        assert record.task_id == "t1"
        assert record.before_performance == 0.3
        assert record.after_performance == 0.6
        assert record.steps == 5
        assert "t1" in at.records

    def test_record_step(self):
        at = AdaptationTracker()
        at.record_step("t1", 0.4)
        at.record_step("t1", 0.7)
        assert len(at.records["t1"]) == 1
        assert at.records["t1"][0].after_performance == 0.7

    def test_adaptation_rate(self):
        at = AdaptationTracker()
        at.record_adaptation("t1", 0.2, 0.4, steps=2)
        at.record_adaptation("t1", 0.4, 0.8, steps=2)
        rate = at.get_adaptation_rate("t1")
        expected = ((0.4 - 0.2) + (0.8 - 0.4)) / 4
        assert abs(rate - expected) < 1e-9

    def test_adaptation_rate_empty(self):
        at = AdaptationTracker()
        assert at.get_adaptation_rate("missing") == 0.0

    def test_convergence_status_converged(self):
        at = AdaptationTracker()
        at.record_adaptation("t1", 0.8, 0.81, steps=1)
        at.record_adaptation("t1", 0.81, 0.815, steps=1)
        status = at.get_convergence_status("t1", threshold=0.01)
        assert status["converged"] is True

    def test_convergence_status_not_converged(self):
        at = AdaptationTracker()
        at.record_adaptation("t1", 0.3, 0.6, steps=1)
        status = at.get_convergence_status("t1", threshold=0.01)
        assert status["converged"] is False
        assert status["reason"] == "insufficient_data" if len(at.records["t1"]) < 2 else "avg_gain"

    def test_stats(self):
        at = AdaptationTracker()
        at.record_adaptation("t1", 0.1, 0.5, steps=1)
        stats = at.get_stats("t1")
        assert stats["num_records"] == 1
        assert stats["latest_performance"] == 0.5
        assert stats["best_performance"] == 0.5

    def test_reset_specific_task(self):
        at = AdaptationTracker()
        at.record_adaptation("t1", 0.1, 0.5)
        at.record_adaptation("t2", 0.2, 0.6)
        at.reset("t1")
        assert "t1" not in at.records
        assert "t2" in at.records

    def test_reset_all(self):
        at = AdaptationTracker()
        at.record_adaptation("t1", 0.1, 0.5)
        at.record_adaptation("t2", 0.2, 0.6)
        at.reset()
        assert at.records == {}
        assert at.latest_step == {}
