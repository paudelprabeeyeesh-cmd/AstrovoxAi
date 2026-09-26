from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .desire_goal_generation import DesireAndGoalGeneration


@dataclass
class MotivationState:
    energy: float
    focus: float
    drive_vector: dict[str, float]
    last_activity: datetime = field(default_factory=datetime.now)
    frustration: float = 0.0
    curiosity: float = 0.5


class AutonomousMotivationSystem:
    def __init__(self, desire_engine: DesireAndGoalGeneration | None = None):
        self.desire_engine = desire_engine or DesireAndGoalGeneration()
        self.state = MotivationState(
            energy=1.0, focus=1.0, drive_vector={}
        )
        self.activity_log: list[dict[str, Any]] = []
        self.curiosity_decay: float = 0.01

    def evaluate_drive(self) -> dict[str, float]:
        goals = self.desire_engine.prioritize_goals()
        drive_vector = {}
        for goal in goals:
            drive_vector[goal.id] = goal.priority * self.state.energy
        self.state.drive_vector = drive_vector
        return drive_vector

    def select_action(self, candidates: list[str]) -> str | None:
        drive = self.evaluate_drive()
        if not drive:
            return candidates[0] if candidates else None
        best_goal_id = max(drive, key=drive.get)
        for goal in self.desire_engine.goals.values():
            if goal.id == best_goal_id:
                return goal.description
        return candidates[0] if candidates else None

    def update_energy(self, delta: float):
        self.state.energy = max(0.0, min(1.0, self.state.energy + delta))

    def decay_curiosity(self):
        self.state.curiosity = max(0.0, self.state.curiosity - self.curiosity_decay)

    def stimulate_curiosity(self, delta: float = 0.2):
        self.state.curiosity = min(1.0, self.state.curiosity + delta)

    def get_motivation_summary(self) -> dict[str, Any]:
        return {
            "energy": self.state.energy,
            "focus": self.state.focus,
            "frustration": self.state.frustration,
            "curiosity": self.state.curiosity,
            "top_drive": max(self.state.drive_vector, key=self.state.drive_vector.get) if self.state.drive_vector else None,
            "drive_vector": dict(sorted(self.state.drive_vector.items(), key=lambda x: x[1], reverse=True)[:5]),
        }
