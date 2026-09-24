import pytest
from temporal_reasoning.scheduling_optimizer import Task, ScheduledTask, SchedulingOptimizer


class TestSchedulingOptimizer:
    def test_add_task(self):
        opt = SchedulingOptimizer()
        opt.add_task("T1", 5.0, resources={"cpu": 1})
        assert "T1" in opt.tasks
        assert opt.tasks["T1"].duration == 5.0

    def test_set_capacity(self):
        opt = SchedulingOptimizer()
        opt.set_capacity("cpu", 4)
        assert opt.resource_capacities["cpu"] == 4

    def test_optimize_simple(self):
        opt = SchedulingOptimizer()
        opt.add_task("T1", 5.0)
        opt.add_task("T2", 3.0)
        schedule = opt.optimize()
        assert len(schedule) == 2
        assert schedule[0].start == 0.0
        assert schedule[0].end == 5.0
        assert schedule[1].start == 0.0
        assert schedule[1].end == 3.0

    def test_optimize_with_dependencies(self):
        opt = SchedulingOptimizer()
        opt.add_task("T1", 5.0)
        opt.add_task("T2", 3.0, dependencies=["T1"])
        schedule = opt.optimize()
        t1 = next(s for s in schedule if s.task_id == "T1")
        t2 = next(s for s in schedule if s.task_id == "T2")
        assert t2.start == pytest.approx(5.0)
        assert t2.end == pytest.approx(8.0)

    def test_makespan(self):
        opt = SchedulingOptimizer()
        opt.add_task("T1", 5.0)
        opt.add_task("T2", 3.0, dependencies=["T1"])
        opt.optimize()
        assert opt.makespan() == pytest.approx(8.0)

    def test_resource_usage_at(self):
        opt = SchedulingOptimizer()
        opt.add_task("T1", 5.0, resources={"cpu": 2})
        opt.add_task("T2", 3.0, resources={"cpu": 1}, dependencies=["T1"])
        opt.optimize()
        usage = opt.resource_usage_at(1.0)
        assert usage["cpu"] == 2
        usage2 = opt.resource_usage_at(6.0)
        assert usage2["cpu"] == 1

    def test_empty_optimize(self):
        opt = SchedulingOptimizer()
        assert opt.optimize() == []
        assert opt.makespan() == 0.0
