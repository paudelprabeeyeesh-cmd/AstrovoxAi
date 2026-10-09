import time

from lifelong_learning.forgetting_mitigator import (
    ForgettingMitigator,
    ImportanceRecord,
)


class TestForgettingMitigator:
    def test_record_importance(self):
        fm = ForgettingMitigator()
        record = fm.record_importance("item1", 0.8)
        assert record.importance == 0.8
        assert record.item_id == "item1"

    def test_record_importance_updates_existing(self):
        fm = ForgettingMitigator()
        fm.record_importance("item1", 0.5)
        record = fm.record_importance("item1", 0.9)
        assert record.importance == 0.9

    def test_get_review_schedule(self):
        fm = ForgettingMitigator(base_interval=10.0, decay=0.5)
        fm.record_importance("item1", 0.8)
        schedule = fm.get_review_schedule("item1")
        assert schedule is not None
        assert schedule["item_id"] == "item1"
        assert schedule["interval"] == 10.0

    def test_get_review_schedule_unknown(self):
        fm = ForgettingMitigator()
        assert fm.get_review_schedule("unknown") is None

    def test_review_increments_count(self):
        fm = ForgettingMitigator()
        fm.record_importance("item1", 0.8)
        entry = fm.review("item1")
        assert entry is not None
        assert entry["review_count"] == 1

    def test_review_unknown_returns_none(self):
        fm = ForgettingMitigator()
        assert fm.review("unknown") is None

    def test_compute_forgetting_curve(self):
        fm = ForgettingMitigator(base_interval=10.0, decay=0.5)
        fm.record_importance("item1", 0.8)
        strength = fm.compute_forgetting_curve("item1", elapsed=10.0)
        assert strength is not None
        assert 0.0 <= strength <= 0.8

    def test_compute_forgetting_curve_unknown(self):
        fm = ForgettingMitigator()
        assert fm.compute_forgetting_curve("unknown", elapsed=10.0) is None

    def test_get_due_items(self):
        fm = ForgettingMitigator(base_interval=0.1)
        fm.record_importance("item1", 0.8)
        fm.record_importance("item2", 0.5)
        time.sleep(0.15)
        due = fm.get_due_items()
        assert "item1" in due
        assert "item2" in due

    def test_get_stats(self):
        fm = ForgettingMitigator()
        fm.record_importance("item1", 0.8)
        fm.record_importance("item2", 0.4)
        fm.review("item1")
        stats = fm.get_stats()
        assert stats["total_items"] == 2
        assert stats["total_reviews"] == 1
