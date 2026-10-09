import numpy as np
from ..goal_management import GoalManagement, Goal


class TestGoal:
    def test_goal_creation(self):
        g = Goal(id="g1", description="test", priority=0.7)
        assert g.id == "g1"
        assert g.status == "active"
        assert g.progress == 0.0

    def test_goal_defaults(self):
        g = Goal(id="g2", description="default")
        assert g.priority == 0.5
        assert g.completed_at is None


class TestGoalManagement:
    def test_create_goal(self):
        gm = GoalManagement()
        goal = gm.create_goal("write code", priority=0.8)
        assert goal.id.startswith("goal_")
        assert len(gm.goals) == 1

    def test_update_progress_completes(self):
        gm = GoalManagement()
        goal = gm.create_goal("task")
        gm.update_progress(goal.id, 1.0)
        assert goal.status == "completed"
        assert goal.completed_at is not None
        assert gm.get_completion_rate() == 1.0

    def test_get_next_goal(self):
        gm = GoalManagement()
        gm.create_goal("low", priority=0.1)
        high = gm.create_goal("high", priority=0.9)
        next_goal = gm.get_next_goal()
        assert next_goal.id == high.id

    def test_complete_goal(self):
        gm = GoalManagement()
        goal = gm.create_goal("task")
        gm.complete_goal(goal.id)
        assert goal.status == "completed"
        assert len(gm.completed) == 1

    def test_max_active_goals(self):
        gm = GoalManagement(max_active_goals=2)
        gm.create_goal("a", priority=0.9)
        gm.create_goal("b", priority=0.8)
        gm.create_goal("c", priority=0.7)
        assert len(gm.goals) == 2

    def test_priority_distribution(self):
        gm = GoalManagement()
        gm.create_goal("a", priority=0.2)
        gm.create_goal("b", priority=0.8)
        dist = gm.get_priority_distribution()
        assert "mean" in dist
        assert np.isclose(dist["mean"], 0.5)

    def test_get_goal_not_found(self):
        gm = GoalManagement()
        assert gm.get_goal("missing") is None
