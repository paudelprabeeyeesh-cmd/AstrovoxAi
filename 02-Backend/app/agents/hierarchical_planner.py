from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GoalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Goal:
    goal_id: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 0
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None


@dataclass
class PlanStep:
    step_id: str
    goal_id: str
    description: str
    action: str
    status: GoalStatus = GoalStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None


class HierarchicalPlanner:
    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.plans: Dict[str, List[PlanStep]] = {}

    def add_goal(self, goal: Goal) -> None:
        self.goals[goal.goal_id] = goal
        if goal.parent_id and goal.parent_id in self.goals:
            self.goals[goal.parent_id].children.append(goal.goal_id)

    def decompose(self, goal_id: str) -> List[PlanStep]:
        if goal_id not in self.goals:
            raise ValueError(f"Unknown goal: {goal_id}")
        goal = self.goals[goal_id]
        steps = self._decompose_goal(goal)
        self.plans[goal_id] = steps
        return steps

    def _decompose_goal(self, goal: Goal) -> List[PlanStep]:
        steps = []
        base_id = f"{goal.goal_id}_step"
        for i, action in enumerate(self._derive_actions(goal)):
            steps.append(PlanStep(
                step_id=f"{base_id}_{i}",
                goal_id=goal.goal_id,
                description=f"Sub-task {i+1} for {goal.description}",
                action=action,
            ))
        return steps

    def _derive_actions(self, goal: Goal) -> List[str]:
        return [
            f"analyze_{goal.goal_id}",
            f"execute_{goal.goal_id}",
            f"validate_{goal.goal_id}",
        ]

    def get_plan(self, goal_id: str) -> List[PlanStep]:
        return self.plans.get(goal_id, [])

    def long_term_plan(self, objective: str, horizon: int = 10) -> List[Goal]:
        goals = []
        for i in range(horizon):
            goals.append(Goal(
                goal_id=f"lt_{objective}_{i}",
                description=f"Long-term milestone {i+1} for {objective}",
                priority=horizon - i,
            ))
        return goals
