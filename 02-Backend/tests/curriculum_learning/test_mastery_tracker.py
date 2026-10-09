import math
import pytest
from curriculum_learning.mastery_tracker import MasteryTracker, MasteryRecord


class TestMasteryRecord:
    def test_initial_state(self):
        record = MasteryRecord(skill_id="s1")
        assert record.mastery_score == 0.0
        assert record.attempts == 0
        assert record.successes == 0

    def test_update_increases_attempts(self):
        record = MasteryRecord(skill_id="s1")
        record.update(0.8)
        assert record.attempts == 1

    def test_update_success(self):
        record = MasteryRecord(skill_id="s1")
        record.update(0.9)
        assert record.successes == 1

    def test_update_failure(self):
        record = MasteryRecord(skill_id="s1")
        record.update(0.5)
        assert record.successes == 0

    def test_is_mastered_before_threshold(self):
        record = MasteryRecord(skill_id="s1")
        record.update(0.6)
        assert record.is_mastered() is False

    def test_is_mastered_after_threshold_and_attempts(self):
        record = MasteryRecord(skill_id="s1")
        for _ in range(3):
            record.update(0.9)
        assert record.is_mastered() is True

    def test_success_rate(self):
        record = MasteryRecord(skill_id="s1")
        record.update(0.9)
        record.update(0.5)
        assert math.isclose(record.success_rate(), 0.5)

    def test_history(self):
        record = MasteryRecord(skill_id="s1")
        record.update(0.5)
        record.update(0.8)
        assert record.history == [0.5, 0.8]

    def test_mastery_score_bounded(self):
        record = MasteryRecord(skill_id="s1")
        for _ in range(20):
            record.update(1.0)
        assert 0.0 <= record.mastery_score <= 1.0


class TestMasteryTracker:
    def test_register_skill(self):
        tracker = MasteryTracker()
        tracker.register_skill("s1")
        assert tracker.get_skill_progress("s1") == 0.0

    def test_record_performance_auto_registers(self):
        tracker = MasteryTracker()
        tracker.record_performance("s1", 0.8)
        assert tracker.get_skill_progress("s1") > 0.0

    def test_get_mastery_not_found(self):
        tracker = MasteryTracker()
        with pytest.raises(KeyError, match="not found"):
            tracker.get_mastery("missing")

    def test_is_mastered_not_registered(self):
        tracker = MasteryTracker()
        assert tracker.is_mastered("missing") is False

    def test_get_mastered_skills(self):
        tracker = MasteryTracker()
        tracker.record_performance("s1", 0.9)
        tracker.record_performance("s1", 0.9)
        tracker.record_performance("s1", 0.9)
        mastered = tracker.get_mastered_skills()
        assert "s1" in mastered

    def test_get_summary(self):
        tracker = MasteryTracker()
        tracker.record_performance("s1", 0.8)
        summary = tracker.get_summary()
        assert "s1" in summary
        assert "mastery_score" in summary["s1"]
        assert "success_rate" in summary["s1"]

    def test_recommend_next_skills(self):
        tracker = MasteryTracker()
        tracker.record_performance("s1", 0.3)
        tracker.record_performance("s2", 0.9)
        recommended = tracker.recommend_next_skills(["s1", "s2"])
        assert recommended[0] == "s1"
