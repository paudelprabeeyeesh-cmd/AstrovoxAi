from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Goal:
    description: str
    priority: float
    source: str
    motivation_type: str
    difficulty: float = 0.5


class IntrinsicMotivation:
    def __init__(self, curiosity_weight: float = 0.3, mastery_weight: float = 0.3, autonomy_weight: float = 0.2, competence_weight: float = 0.2):
        self.curiosity_weight = curiosity_weight
        self.mastery_weight = mastery_weight
        self.autonomy_weight = autonomy_weight
        self.competence_weight = competence_weight
        self.mastery_history: List[str] = []

    def compute_drive(self, goal: Goal, past_performance: float) -> float:
        curiosity = self._curiosity_drive(goal) if goal.motivation_type == "curiosity" else 0.0
        mastery = self._mastery_drive(goal, past_performance) if goal.motivation_type == "mastery" else 0.0
        autonomy = self._autonomy_drive(goal) if goal.motivation_type == "autonomy" else 0.0
        competence = self._competence_drive(past_performance) if goal.motivation_type == "competence" else 0.0
        drive = (self.curiosity_weight * curiosity + self.mastery_weight * mastery +
                 self.autonomy_weight * autonomy + self.competence_weight * competence)
        return max(0.0, min(1.0, drive))

    def _curiosity_drive(self, goal: Goal) -> float:
        return goal.difficulty / max(1.0, goal.difficulty + 0.1)

    def _mastery_drive(self, goal: Goal, past_performance: float) -> float:
        mastery_gap = max(0.0, 1.0 - past_performance)
        return mastery_gap * goal.priority

    def _autonomy_drive(self, goal: Goal) -> float:
        return goal.priority * 0.7 + 0.3

    def _competence_drive(self, past_performance: float) -> float:
        return 1.0 / max(past_performance + 1e-6, 0.1)


class GoalGenerator:
    def __init__(self):
        self.goals: List[Goal] = []
        self.motivation = IntrinsicMotivation()

    def generate(self, context: str, motivation_types: Optional[List[str]] = None) -> List[Goal]:
        motivation_types = motivation_types or ["curiosity", "mastery", "autonomy", "competence"]
        generated = []
        for mtype in motivation_types:
            goal = Goal(description=f"{mtype}: {context}", priority=0.5, source="intrinsic", motivation_type=mtype)
            drive = self.motivation.compute_drive(goal, 0.5)
            goal.priority = drive
            generated.append(goal)
        self.goals.extend(generated)
        return generated

    def prioritize(self) -> List[Goal]:
        return sorted(self.goals, key=lambda g: g.priority, reverse=True)

    def filter_achievable(self, capability_level: float) -> List[Goal]:
        return [g for g in self.goals if g.difficulty <= capability_level]
