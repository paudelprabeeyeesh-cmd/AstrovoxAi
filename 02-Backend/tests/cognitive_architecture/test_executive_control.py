import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.executive_control import (
    ExecutiveControlSystem,
    TaskSet,
    TaskSwitchingCost,
    InhibitoryControl,
)


class TestTaskSet:
    def test_utility_decays(self):
        task = TaskSet(name="t1", rules={}, priority=1.0, created_at=0.0)
        utility = task.get_utility(current_time=10.0)
        assert utility < 1.0

    def test_utility_high_when_recent(self):
        task = TaskSet(name="t1", rules={}, priority=1.0)
        utility = task.get_utility(current_time=time.time())
        assert utility > 0.9


class TestTaskSwitchingCost:
    def test_switch_cost_computed(self):
        tsc = TaskSwitchingCost(base_cost=0.2)
        from_task = TaskSet(name="t1", rules={"mode": "read"}, priority=1.0)
        to_task = TaskSet(name="t2", rules={"mode": "write"}, priority=1.0)
        cost = tsc.compute_switch_cost(from_task, to_task)
        assert 0.0 <= cost <= 1.0

    def test_similar_rules_lower_cost(self):
        tsc = TaskSwitchingCost(base_cost=0.2)
        from_task = TaskSet(name="t1", rules={"mode": "read", "format": "json"}, priority=1.0)
        to_task = TaskSet(name="t2", rules={"mode": "read", "format": "xml"}, priority=1.0)
        cost = tsc.compute_switch_cost(from_task, to_task)
        similar_cost = tsc.compute_switch_cost(from_task, from_task)
        assert cost < similar_cost


class TestInhibitoryControl:
    def test_inhibit_and_suppress(self):
        ic = InhibitoryControl(inhibition_strength=0.8)
        ic.inhibit("item1")
        suppression = ic.get_suppression("item1")
        assert suppression > 0.5

    def test_release_removes_suppression(self):
        ic = InhibitoryControl(inhibition_strength=0.8, recovery_rate=1.0)
        ic.inhibit("item1")
        suppression_before = ic.get_suppression("item1")
        assert suppression_before > 0.0
        ic.step(dt=5.0)
        suppression_after = ic.get_suppression("item1")
        assert suppression_after < suppression_before

    def test_unknown_item_zero_suppression(self):
        ic = InhibitoryControl()
        assert ic.get_suppression("nonexistent") == 0.0


class TestExecutiveControlSystem:
    def test_add_task(self):
        ecs = ExecutiveControlSystem(max_active_tasks=2)
        task = TaskSet(name="t1", rules={}, priority=1.0)
        assert ecs.add_task(task)
        assert "t1" in ecs.task_sets

    def test_add_task_eviction(self):
        ecs = ExecutiveControlSystem(max_active_tasks=1)
        ecs.add_task(TaskSet(name="low", rules={}, priority=0.3))
        ecs.add_task(TaskSet(name="high", rules={}, priority=0.9))
        assert "high" in ecs.task_sets
        assert "low" not in ecs.task_sets

    def test_switch_task_cost(self):
        ecs = ExecutiveControlSystem(max_active_tasks=4)
        ecs.add_task(TaskSet(name="t1", rules={"mode": "read"}, priority=1.0))
        ecs.add_task(TaskSet(name="t2", rules={"mode": "write"}, priority=1.0))
        ecs.active_task = "t1"
        cost = ecs.switch_task("t2")
        assert ecs.active_task == "t2"
        assert cost > 0.0

    def test_switch_unknown_raises(self):
        ecs = ExecutiveControlSystem()
        with pytest.raises(ValueError):
            ecs.switch_task("nonexistent")

    def test_set_goal_switches(self):
        ecs = ExecutiveControlSystem()
        ecs.add_task(TaskSet(name="goal_task", rules={}, priority=1.0))
        ecs.set_goal("goal_task")
        assert ecs.active_task == "goal_task"

    def test_pop_goal(self):
        ecs = ExecutiveControlSystem()
        ecs.set_goal("g1")
        popped = ecs.pop_goal()
        assert popped == "g1"
        assert ecs.pop_goal() is None

    def test_execute_action_no_active_task(self):
        ecs = ExecutiveControlSystem()
        with pytest.raises(RuntimeError):
            ecs.execute_action(lambda: 42, "ctx")

    def test_execute_action_returns_result(self):
        ecs = ExecutiveControlSystem()
        ecs.add_task(TaskSet(name="t1", rules={}, priority=1.0))
        ecs.active_task = "t1"
        result = ecs.execute_action(lambda: 99, "ctx")
        assert result == 99

    def test_get_performance_metrics(self):
        ecs = ExecutiveControlSystem()
        ecs.add_task(TaskSet(name="t1", rules={}, priority=1.0))
        ecs.add_task(TaskSet(name="t2", rules={}, priority=1.0))
        ecs.active_task = "t1"
        ecs.switch_task("t2")
        metrics = ecs.get_performance_metrics()
        assert "avg_switch_cost" in metrics
        assert metrics["total_actions"] >= 1
