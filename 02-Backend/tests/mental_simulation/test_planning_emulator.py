import pytest
from mental_simulation.planning_emulator import PlanningEmulator, Plan, ExecutionResult


class TestPlanningEmulator:
    def test_emulate_basic_plan(self):
        emulator = PlanningEmulator(max_steps=5)
        result = emulator.emulate("reach goal", {"steps": ["a", "b"], "expected_success_rate": 0.8})
        assert isinstance(result, ExecutionResult)
        assert result.plan.goal == "reach goal"
        assert len(result.plan.steps) == 2

    def test_emulate_respects_max_steps(self):
        emulator = PlanningEmulator(max_steps=2)
        result = emulator.emulate("goal", {"steps": ["a", "b", "c", "d"]})
        assert len(result.plan.steps) == 2

    def test_replan_excludes_failed_steps(self):
        emulator = PlanningEmulator()
        original = emulator.emulate("goal", {"steps": ["a", "b", "c"]})
        replanned = emulator.replan(original, {"failed_steps": ["a"], "expected_success_rate": 0.9})
        assert "a" not in replanned.plan.steps

    def test_history_records_results(self):
        emulator = PlanningEmulator()
        emulator.emulate("goal", {"steps": ["a"]})
        assert len(emulator.history) == 1

    def test_plan_goal_stored(self):
        emulator = PlanningEmulator()
        result = emulator.emulate("reach goal", {"steps": ["a"]})
        assert result.plan.goal == "reach goal"

    def test_execution_result_fields(self):
        emulator = PlanningEmulator()
        result = emulator.emulate("goal", {"steps": ["a", "b"]})
        assert result.success is True
        assert result.steps_completed == 2
        assert len(result.outcomes) == 2

    def test_emulate_empty_steps(self):
        emulator = PlanningEmulator()
        result = emulator.emulate("goal", {"steps": []})
        assert result.steps_completed == 0
        assert result.outcomes == []

    def test_emulate_success_rate_threshold(self):
        emulator = PlanningEmulator()
        result = emulator.emulate("goal", {"steps": ["a"], "expected_success_rate": 0.4})
        assert result.success is False

    def test_replan_preserves_goal(self):
        emulator = PlanningEmulator()
        original = emulator.emulate("reach goal", {"steps": ["a", "b"]})
        replanned = emulator.replan(original, {"failed_steps": ["a"], "expected_success_rate": 0.9})
        assert replanned.plan.goal == "reach goal"
