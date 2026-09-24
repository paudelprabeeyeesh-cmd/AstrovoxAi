from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CompetenceConfig:
    alpha: float = 0.1
    threshold: float = 0.8
    window_size: int = 10


class CompetenceEstimator:
    def __init__(self, config: Optional[CompetenceConfig] = None):
        self.config = config or CompetenceConfig()
        self.scores: List[float] = []
        self.competence: float = 0.0

    def update(self, score: float) -> None:
        self.scores.append(score)
        if len(self.scores) > self.config.window_size:
            self.scores.pop(0)
        self.competence = sum(self.scores) / len(self.scores)

    def get_competence(self) -> float:
        return self.competence

    def is_competent(self) -> bool:
        return self.competence >= self.config.threshold

    def reset(self) -> None:
        self.scores = []
        self.competence = 0.0
