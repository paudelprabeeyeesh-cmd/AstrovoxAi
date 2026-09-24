import numpy as np
import pytest
from ..social_learning import SocialLearning


class TestSocialLearning:
    def test_observe(self):
        sl = SocialLearning()
        sl.observe("peer1", "task_a", "action_1", 0.8)
        assert len(sl.demonstrations) == 1
        assert len(sl.teachers["peer1"]) == 1

    def test_imitate_best(self):
        sl = SocialLearning(imitation_rate=1.0)
        sl.observe("peer1", "task_x", "action_best", 0.9)
        sl.observe("peer1", "task_x", "action_other", 0.3)
        action = sl.imitate_best("task_x")
        assert action == "action_best"

    def test_imitate_no_match(self):
        sl = SocialLearning()
        assert sl.imitate_best("unknown_task") is None

    def test_learn_from_peer(self):
        sl = SocialLearning()
        sl.observe("peer1", "t1", "a1", 0.9)
        sl.observe("peer1", "t1", "a2", 0.3)
        repertoire = sl.learn_from_peer("peer1")
        assert "peer1" in sl.repertoire
        assert repertoire["a1"] > repertoire["a2"]

    def test_get_imitation_candidates(self):
        sl = SocialLearning()
        for i in range(5):
            sl.observe("p", "task", f"a{i}", float(i) / 4.0)
        candidates = sl.get_imitation_candidates("task", top_k=3)
        assert len(candidates) == 3
        assert candidates[0].outcome == 1.0

    def test_social_repertoire_summary(self):
        sl = SocialLearning()
        sl.observe("a", "t", "x", 0.5)
        summary = sl.social_repertoire_summary()
        assert summary["total_demonstrations"] == 1
        assert summary["peers"] == ["a"]

    def test_buffer_overflow(self):
        sl = SocialLearning(observation_window=2)
        sl.observe("p", "t", "a", 0.5)
        sl.observe("p", "t", "b", 0.5)
        sl.observe("p", "t", "c", 0.5)
        assert len(sl.teachers["p"]) == 2
