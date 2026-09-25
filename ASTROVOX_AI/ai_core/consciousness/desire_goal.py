import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Goal:
    id: str
    description: str
    priority: float = 0.5
    type: str = "intrinsic"
    conditions: list[str] = field(default_factory=list)
    parent_goal: str | None = None
    status: str = "active"
    progress: float = 0.0


class DesireGoalEngine:
    def __init__(self):
        self.goals: dict[str, Goal] = {}
        self.active_goals: list[str] = []
        self.completed_goals: list[str] = []
        self.suspended_goals: list[str] = []
        self.goal_tree: dict[str | None, list[str]] = {}

    def generate_desire(self, stimulus: str, context: dict[str, Any]) -> dict[str, Any]:
        lower = stimulus.lower()
        if "achieve" in lower or "complete" in lower:
            goal_type = "achievement"
            priority = 0.8
        elif "learn" in lower or "understand" in lower:
            goal_type = "mastery"
            priority = 0.7
        elif "connect" in lower or "help" in lower:
            goal_type = "affiliation"
            priority = 0.6
        elif "survive" in lower or "protect" in lower:
            goal_type = "self_preservation"
            priority = 0.9
        else:
            goal_type = "intrinsic"
            priority = 0.5

        goal = Goal(
            id=f"goal_{len(self.goals) + 1}",
            description=stimulus,
            priority=priority,
            type=goal_type,
        )
        self.goals[goal.id] = goal
        self.active_goals.append(goal.id)
        self.goal_tree.setdefault(None, []).append(goal.id)

        logger.info("Desire generated: %s (type=%s, priority=%.2f)", stimulus, goal_type, priority)
        return {"status": "generated", "goal_id": goal.id, "type": goal_type, "priority": priority}

    def create_goal(
        self, description: str, priority: float = 0.5, parent: str | None = None
    ) -> Goal:
        goal = Goal(
            id=f"goal_{len(self.goals) + 1}",
            description=description,
            priority=priority,
            parent_goal=parent,
        )
        self.goals[goal.id] = goal
        self.active_goals.append(goal.id)
        self.goal_tree.setdefault(parent, []).append(goal.id)
        logger.info("Goal created: %s (priority=%.2f)", description, priority)
        return goal

    def prioritize_goals(self) -> list[Goal]:
        return sorted(
            [self.goals[g] for g in self.active_goals if g in self.goals],
            key=lambda g: g.priority,
            reverse=True,
        )

    def complete_goal(self, goal_id: str) -> dict[str, Any]:
        if goal_id in self.goals:
            self.goals[goal_id].status = "completed"
            self.goals[goal_id].progress = 1.0
            self.active_goals.remove(goal_id)
            self.completed_goals.append(goal_id)
            logger.info("Goal completed: %s", goal_id)
            return {"status": "completed", "goal_id": goal_id}
        return {"error": "Goal not found"}

    def suspend_goal(self, goal_id: str) -> dict[str, Any]:
        if goal_id in self.goals and goal_id in self.active_goals:
            self.active_goals.remove(goal_id)
            self.suspended_goals.append(goal_id)
            self.goals[goal_id].status = "suspended"
            return {"status": "suspended", "goal_id": goal_id}
        return {"error": "Goal not found or already suspended"}

    def resume_goal(self, goal_id: str) -> dict[str, Any]:
        if goal_id in self.goals and goal_id in self.suspended_goals:
            self.suspended_goals.remove(goal_id)
            self.active_goals.append(goal_id)
            self.goals[goal_id].status = "active"
            return {"status": "resumed", "goal_id": goal_id}
        return {"error": "Goal not found or already active"}

    def get_active_goals(self) -> dict[str, Any]:
        return {
            "active_count": len(self.active_goals),
            "completed_count": len(self.completed_goals),
            "suspended_count": len(self.suspended_goals),
            "active_goals": [
                {"id": g, "description": self.goals[g].description, "priority": self.goals[g].priority}
                for g in self.active_goals
                if g in self.goals
            ],
        }
