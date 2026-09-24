import pytest
import numpy as np
from agi_core.goal_generation import GoalGenerator, IntrinsicMotivation, Goal


class TestGoalGenerator:
    def test_generate_returns_list(self):
        gen = GoalGenerator()
        goals = gen.generate("test context")
        assert len(goals) == 4

    def test_prioritize_sorted(self):
        gen = GoalGenerator()
        gen.generate("ctx")
        prioritized = gen.prioritize()
        assert all(prioritized[i].priority >= prioritized[i + 1].priority for i in range(len(prioritized) - 1))

    def test_filter_achievable(self):
        gen = GoalGenerator()
        goals = gen.generate("ctx")
        achievable = gen.filter_achievable(1.0)
        assert len(achievable) <= len(goals)

    def test_motivation_drive(self):
        motivation = IntrinsicMotivation()
        g = Goal(description="test", priority=0.5, source="int", motivation_type="mastery")
        drive = motivation.compute_drive(g, 0.3)
        assert 0.0 <= drive <= 1.0
