from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Desire:
    id: str
    description: str
    strength: float
    category: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Goal:
    id: str
    description: str
    priority: float
    parent_desire_id: str | None = None
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)


class DesireAndGoalGeneration:
    def __init__(self):
        self.desires: dict[str, Desire] = {}
        self.goals: dict[str, Goal] = {}
        self.goal_hierarchy: dict[str | None, list[str]] = {}

    def generate_desire(self, description: str, strength: float, category: str = "intrinsic") -> Desire:
        desire = Desire(
            id=f"desire_{len(self.desires)+1}",
            description=description,
            strength=max(0.0, min(1.0, strength)),
            category=category,
        )
        self.desires[desire.id] = desire
        self.goal_hierarchy.setdefault(None, []).append(desire.id)
        return desire

    derive_goal_from_desire = lambda self, desire_id, description, priority=0.5: self._derive_goal(desire_id, description, priority)

    def _derive_goal(self, desire_id: str, description: str, priority: float) -> Goal:
        goal = Goal(
            id=f"goal_{len(self.goals)+1}",
            description=description,
            priority=max(0.0, min(1.0, priority)),
            parent_desire_id=desire_id,
        )
        self.goals[goal.id] = goal
        self.goal_hierarchy.setdefault(desire_id, []).append(goal.id)
        return goal

    def prioritize_goals(self) -> list[Goal]:
        active = [g for g in self.goals.values() if g.status == "active"]
        return sorted(active, key=lambda g: g.priority, reverse=True)

    def get_goal_tree(self) -> dict[str, Any]:
        return {
            "total_desires": len(self.desires),
            "total_goals": len(self.goals),
            "active_goals": sum(1 for g in self.goals.values() if g.status == "active"),
            "top_goals": [g.description for g in self.prioritize_goals()[:5]],
        }
