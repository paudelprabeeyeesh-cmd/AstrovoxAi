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
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class DesireAndGoalGeneration:
    def __init__(self):
        self.desires: dict[str, Desire] = {}
        self.goals: dict[str, Goal] = {}
        self.goal_hierarchy: dict[str | None, list[str]] = {}
        self.category_weights = {
            "self_preservation": 1.0,
            "intrinsic": 0.8,
            "achievement": 0.7,
            "mastery": 0.6,
            "affiliation": 0.5,
            "unknown": 0.3,
        }

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
        category_weighted = []
        for g in self.goals.values():
            if g.status == "active":
                weight = self.category_weights.get(g.parent_desire_id, 0.5) if g.parent_desire_id else 0.5
                adjusted_priority = g.priority * weight
                category_weighted.append((adjusted_priority, g))
        category_weighted.sort(key=lambda x: x[0], reverse=True)
        return [g for _, g in category_weighted]

    def get_goal_tree(self) -> dict[str, Any]:
        return {
            "total_desires": len(self.desires),
            "total_goals": len(self.goals),
            "active_goals": sum(1 for g in self.goals.values() if g.status == "active"),
            "top_goals": [g.description for g in self.prioritize_goals()[:5]],
        }
