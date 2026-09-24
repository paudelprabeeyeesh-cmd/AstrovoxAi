import pytest
from advanced_reasoning.planning_engine import PlanningEngine, Task


class TestPlanningEngine:
    def test_decompose_flat_task(self):
        engine = PlanningEngine()
        task = Task(id="t1", description="Root task", dependencies=[], complexity=2.0, estimated_tokens=200)
        plan = engine.decompose(task)
        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == "t1"
        assert plan.total_complexity == 2.0

    def test_layer_ordering(self):
        engine = PlanningEngine()
        task = Task(id="root", description="Root", dependencies=["a", "b"], complexity=1.0)
        plan = engine.decompose(task)
        all_items = [item for sublist in plan.layers for item in sublist]
        assert "a" in all_items
        assert "b" in all_items
        assert "root" in all_items
        assert all_items.index("a") < all_items.index("root")
        assert all_items.index("b") < all_items.index("root")

    def test_decompose_with_dependencies(self):
        engine = PlanningEngine()
        task = Task(id="t1", description="Root", dependencies=["d1", "d2"], complexity=3.0)
        plan = engine.decompose(task)
        ids = [t.id for t in plan.tasks]
        assert "d1" in ids
        assert "d2" in ids
        assert "t1" in ids

    def test_circular_dependency_raises(self):
        engine = PlanningEngine()
        task = Task(id="a", description="A", dependencies=["b"], complexity=1.0)
        plan = engine.decompose(task)
        for t in plan.tasks:
            if t.id == "b":
                t.dependencies = ["a"]
        with pytest.raises(ValueError, match="Circular dependency"):
            engine._resolve_layers(plan.tasks)

    def test_estimate_execution_time(self):
        engine = PlanningEngine()
        task = Task(id="t1", description="T", dependencies=[], complexity=1.0, estimated_tokens=1000)
        plan = engine.decompose(task)
        timing = engine.estimate_execution_time(plan)
        assert "total_layers" in timing
        assert timing["estimated_seconds"] > 0

    def test_max_layer_size(self):
        engine = PlanningEngine(max_layer_size=1)
        task = Task(id="root", description="Root", dependencies=["a", "b"], complexity=1.0)
        plan = engine.decompose(task)
        for layer in plan.layers:
            assert len(layer) <= 1
