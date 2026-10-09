import pytest
from complex_learning.curriculum_manager import CurriculumManager, Topic


class TestCurriculumManager:
    def test_initialization(self):
        cm = CurriculumManager(mastery_threshold=0.8, decay=0.1)
        assert cm.mastery_threshold == 0.8
        assert cm.decay == 0.1
        assert cm.get_progress() == 0.0

    def test_add_topic(self):
        cm = CurriculumManager()
        cm.add_topic("math", difficulty=0.3)
        cm.add_topic("algebra", difficulty=0.5, dependencies=["math"])
        assert "math" in cm.topics
        assert cm.topics["algebra"].dependencies == ["math"]

    def test_add_topic_missing_dependency(self):
        cm = CurriculumManager()
        with pytest.raises(ValueError):
            cm.add_topic("algebra", dependencies=["math"])

    def test_update_mastery(self):
        cm = CurriculumManager()
        cm.add_topic("math")
        cm.update_mastery("math", 0.9)
        assert abs(cm.topics["math"].mastery - 0.09) < 1e-9

    def test_schedule_next(self):
        cm = CurriculumManager()
        cm.add_topic("a", difficulty=0.9)
        cm.add_topic("b", difficulty=0.1)
        next_topic = cm.schedule_next()
        assert next_topic == "b"

    def test_schedule_next_blocked_by_dependency(self):
        cm = CurriculumManager()
        cm.add_topic("a")
        cm.add_topic("b", dependencies=["a"])
        next_topic = cm.schedule_next()
        assert next_topic == "a"

    def test_schedule_next_none_when_all_mastered(self):
        cm = CurriculumManager(mastery_threshold=0.5)
        cm.add_topic("a")
        cm.update_mastery("a", 1.0)
        assert cm.schedule_next() is None

    def test_mastered(self):
        cm = CurriculumManager(mastery_threshold=0.5)
        cm.add_topic("a")
        cm.add_topic("b")
        cm.update_mastery("a", 1.0)
        assert cm.mastered() == ["a"]

    def test_get_progress(self):
        cm = CurriculumManager()
        cm.add_topic("a")
        cm.add_topic("b")
        cm.update_mastery("a", 1.0)
        cm.update_mastery("b", 0.0)
        assert abs(cm.get_progress() - 0.5) < 1e-9

