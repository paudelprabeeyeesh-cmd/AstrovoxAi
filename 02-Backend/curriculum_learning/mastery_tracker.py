import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class MasteryRecord:
    skill_id: str
    mastery_score: float = 0.0
    attempts: int = 0
    successes: int = 0
    history: List[float] = field(default_factory=list)

    def update(self, performance: float, threshold: float = 0.7) -> None:
        self.attempts += 1
        self.history.append(performance)
        if performance >= threshold:
            self.successes += 1
        alpha = 0.1
        self.mastery_score = (1 - alpha) * self.mastery_score + alpha * performance
        self.mastery_score = max(0.0, min(1.0, self.mastery_score))

    def is_mastered(self, threshold: float = 0.85) -> bool:
        return self.mastery_score >= threshold and self.attempts >= 3

    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class MasteryTracker:
    def __init__(self, mastery_threshold: float = 0.85, success_threshold: float = 0.7):
        self.mastery_threshold = mastery_threshold
        self.success_threshold = success_threshold
        self._records: Dict[str, MasteryRecord] = {}

    def register_skill(self, skill_id: str) -> None:
        if skill_id not in self._records:
            self._records[skill_id] = MasteryRecord(skill_id=skill_id)

    def record_performance(self, skill_id: str, performance: float) -> MasteryRecord:
        if skill_id not in self._records:
            self.register_skill(skill_id)
        record = self._records[skill_id]
        record.update(performance, threshold=self.success_threshold)
        return record

    def get_mastery(self, skill_id: str) -> MasteryRecord:
        if skill_id not in self._records:
            raise KeyError(f"Skill {skill_id} not found")
        return self._records[skill_id]

    def is_mastered(self, skill_id: str) -> bool:
        if skill_id not in self._records:
            return False
        return self._records[skill_id].is_mastered(threshold=self.mastery_threshold)

    def get_mastered_skills(self) -> List[str]:
        return [skill_id for skill_id, record in self._records.items() if record.is_mastered(threshold=self.mastery_threshold)]

    def get_skill_progress(self, skill_id: str) -> float:
        if skill_id not in self._records:
            return 0.0
        return self._records[skill_id].mastery_score

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        summary = {}
        for skill_id, record in self._records.items():
            summary[skill_id] = {
                "mastery_score": record.mastery_score,
                "success_rate": record.success_rate(),
                "attempts": record.attempts,
                "mastered": record.is_mastered(threshold=self.mastery_threshold),
            }
        return summary

    def recommend_next_skills(self, all_skills: List[str]) -> List[str]:
        unmastered = [s for s in all_skills if not self.is_mastered(s)]
        unmastered.sort(key=lambda s: self.get_skill_progress(s))
        return unmastered
