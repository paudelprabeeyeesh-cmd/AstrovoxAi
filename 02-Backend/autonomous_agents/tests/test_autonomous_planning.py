import numpy as np
import pytest
from ..autonomous_planning import AutonomousPlanning, Plan


class TestAutonomousPlanning:
    def test_create_plan(self):
        ap = AutonomousPlanning(max_horizon=10)
        plan = ap.create_plan("solve x", ["step1", "step2"])
        assert plan.goal == "solve x"
        assert len(plan.steps) == 2

    def test_expand_horizon(self):
        ap = AutonomousPlanning(max_horizon=5)
        plan = ap.create_plan("goal", ["a"])
        ap.expand_horizon(plan.id, ["b", "c", "d", "e"])
        assert len(plan.steps) == 5
        assert plan.horizon == 5

    def test_expand_horizon_respects_max(self):
        ap = AutonomousPlanning(max_horizon=3)
        plan = ap.create_plan("goal", ["a"])
        ap.expand_horizon(plan.id, ["b", "c", "d", "e", "f"])
        assert len(plan.steps) == 3

    def test_evaluate_plan(self):
        ap = AutonomousPlanning()
        plan = ap.create_plan("goal", ["x", "y"])
        state = {"x": 1.0, "y": 0.0}
        utility = ap.evaluate_plan(plan.id, state)
        assert utility is not None
        assert 0.0 <= utility <= 1.0

    def test_execute_step(self):
        ap = AutonomousPlanning()
        plan = ap.create_plan("goal", ["alpha", "beta"])
        ok, step = ap.execute_step(plan.id, 0)
        assert ok is True
        assert step == "alpha"

    def test_execute_step_invalid(self):
        ap = AutonomousPlanning()
        plan = ap.create_plan("goal", ["a"])
        ok, step = ap.execute_step(plan.id, 5)
        assert ok is False

    def test_get_open_world_plan(self):
        ap = AutonomousPlanning(max_horizon=5)
        plan = ap.get_open_world_plan("explore", ["a", "b", "c"])
        assert plan.goal == "explore"
        assert len(plan.steps) <= 5

    def test_adapt_plan(self):
        ap = AutonomousPlanning()
        plan = ap.create_plan("goal", ["a", "b", "c"])
        rewards = {"a": 0.9, "b": 0.1, "c": 0.5}
        adapted = ap.adapt_plan(plan.id, rewards)
        assert adapted is not None
        assert adapted.steps[0] == "a"
