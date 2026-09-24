from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np


@dataclass
class Goal:
    id: str
    description: str
    priority: float = 0.5
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, float] = field(default_factory=dict)


class GoalManagement:
    def __init__(self, max_active_goals: int = 50):
        self.max_active_goals = max_active_goals
        self.goals: Dict[str, Goal] = {}
        self.goal_queue: List[str] = []
        self.completed: List[Goal] = []
        self._counter = 0

    def create_goal(self, description: str, priority: float = 0.5) -> Goal:
        if len(self.goals) >= self.max_active_goals:
            self._promote_lowest_priority()
        self._counter += 1
        goal = Goal(
            id=f"goal_{self._counter}",
            description=description,
            priority=max(0.0, min(1.0, priority)),
        )
        self.goals[goal.id] = goal
        self.goal_queue.append(goal.id)
        return goal

    def update_progress(self, goal_id: str, progress_delta: float) -> Optional[Goal]:
        goal = self.goals.get(goal_id)
        if goal is None:
            return None
        goal.progress = max(0.0, min(1.0, goal.progress + progress_delta))
        if goal.progress >= 1.0:
            goal.status = "completed"
            goal.completed_at = datetime.utcnow().isoformat()
            goal.progress = 1.0
            self.completed.append(goal)
            if goal_id in self.goals:
                del self.goals[goal_id]
            if goal_id in self.goal_queue:
                self.goal_queue.remove(goal_id)
        return goal

    def get_active_goals(self) -> List[Goal]:
        return [g for g in self.goals.values() if g.status == "active"]

    def get_next_goal(self) -> Optional[Goal]:
        active = [gid for gid in self.goal_queue if self.goals[gid].status == "active"]
        if not active:
            return None
        best = max(active, key=lambda gid: self.goals[gid].priority)
        return self.goals[best]

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self.goals.get(goal_id)

    def complete_goal(self, goal_id: str) -> Optional[Goal]:
        goal = self.goals.get(goal_id)
        if goal is None or goal.status == "completed":
            return goal
        return self.update_progress(goal_id, 1.0 - goal.progress)

    def get_completion_rate(self) -> float:
        total = len(self.goals) + len(self.completed)
        if total == 0:
            return 0.0
        return len(self.completed) / total

    def get_priority_distribution(self) -> Dict[str, float]:
        active = self.get_active_goals()
        if not active:
            return {}
        priorities = [g.priority for g in active]
        return {
            "mean": float(np.mean(priorities)),
            "std": float(np.std(priorities)),
            "max": float(np.max(priorities)),
            "min": float(np.min(priorities)),
        }

    def _promote_lowest_priority(self) -> None:
        active = self.get_active_goals()
        if not active:
            return
        lowest = min(active, key=lambda g: g.priority)
        if lowest.id in self.goals:
            del self.goals[lowest.id]
            if lowest.id in self.goal_queue:
                self.goal_queue.remove(lowest.id)
