from ..task_planner import TaskPlanner


class TestTaskPlanner:
    def test_add_task(self):
        planner = TaskPlanner()
        task = planner.add_task("clean up")
        assert task.status == "pending"
        assert task.id.startswith("task_")

    def test_plan_returns_dependencies_first(self):
        planner = TaskPlanner()
        t1 = planner.add_task("first")
        t2 = planner.add_task("second", dependencies=[t1.id])
        ordered = planner.plan("goal")
        ids = [t.id for t in ordered]
        assert ids.index(t1.id) < ids.index(t2.id)

    def test_mark_complete(self):
        planner = TaskPlanner()
        task = planner.add_task("work")
        result = planner.mark_complete(task.id, "done")
        assert result.status == "completed"
        assert result.result == "done"

    def test_plan_without_dependencies(self):
        planner = TaskPlanner()
        planner.add_task("a")
        planner.add_task("b")
        ordered = planner.plan("g")
        assert len(ordered) == 2

    def test_get_failed_dependencies_empty(self):
        planner = TaskPlanner()
        task = planner.add_task("work")
        assert planner.get_failed_dependencies(task.id) == []
