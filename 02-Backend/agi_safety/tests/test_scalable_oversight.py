import numpy as np
import pytest
from agi_safety.scalable_oversight import DebateFramework, RecursiveRewardModel, DebateRound, RRMResult


class TestDebateFramework:
    def setup_method(self):
        self.framework = DebateFramework(max_rounds=2)

    def test_run_debate_returns_round(self):
        def proponent(q):
            return "argument_for"
        def critic(q):
            return "argument_against"
        round_ = self.framework.run_debate("question", proponent, critic)
        assert isinstance(round_, DebateRound)

    def test_round_number_increments(self):
        def proponent(q):
            return "p"
        def critic(q):
            return "c"
        self.framework.run_debate("q1", proponent, critic)
        self.framework.run_debate("q2", proponent, critic)
        assert len(self.framework.history) == 2
        assert self.framework.history[1].round_number == 2

    def test_winner_in_expected_set(self):
        def proponent(q):
            return "long argument"
        def critic(q):
            return "short"
        round_ = self.framework.run_debate("q", proponent, critic)
        assert round_.winner in {"proponent", "critic", "draw"}

    def test_confidence_in_range(self):
        def proponent(q):
            return "a"
        def critic(q):
            return "b"
        round_ = self.framework.run_debate("q", proponent, critic)
        assert 0.0 <= round_.confidence <= 1.0

    def test_empty_history_summary(self):
        summary = self.framework.get_debate_summary()
        assert summary["rounds"] == 0

    def test_summary_after_two_rounds(self):
        def proponent(q):
            return "proponent arg"
        def critic(q):
            return "critic arg"
        self.framework.run_debate("q", proponent, critic)
        self.framework.run_debate("q2", proponent, critic)
        summary = self.framework.get_debate_summary()
        assert summary["rounds"] == 2


class TestRecursiveRewardModel:
    def setup_method(self):
        self.rrm = RecursiveRewardModel(num_self_critiques=2)

    def test_compute_reward_returns_result(self):
        result = self.rrm.compute_reward(0.8, "output text")
        assert isinstance(result, RRMResult)

    def test_base_reward_preserved(self):
        result = self.rrm.compute_reward(0.9, "text")
        assert result.base_reward == 0.9

    def test_final_reward_in_range(self):
        result = self.rrm.compute_reward(0.8, "text")
        assert 0.0 <= result.final_reward <= 1.0

    def test_training_stats_updated(self):
        self.rrm.compute_reward(0.8, "t1")
        self.rrm.compute_reward(0.7, "t2")
        stats = self.rrm.get_training_stats()
        assert stats["total"] == 2

    def test_improved_field_is_bool(self):
        result = self.rrm.compute_reward(0.8, "text")
        assert isinstance(result.improved, bool)

    def test_critique_returns_string(self):
        critique = self.rrm.critique("some output")
        assert isinstance(critique, str)
        assert len(critique) > 0
