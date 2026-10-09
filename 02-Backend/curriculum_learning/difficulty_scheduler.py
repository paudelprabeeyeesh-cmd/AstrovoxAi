import math
from typing import Callable, Dict, List, Optional, Tuple


class DifficultyScheduler:
    def __init__(
        self,
        start_difficulty: float = 0.1,
        end_difficulty: float = 1.0,
        schedule: str = "linear",
        warmup_epochs: int = 5,
        max_epochs: int = 50,
    ):
        self.start_difficulty = start_difficulty
        self.end_difficulty = end_difficulty
        self.schedule = schedule
        self.warmup_epochs = warmup_epochs
        self.max_epochs = max(max_epochs, warmup_epochs + 1)
        self.current_difficulty = start_difficulty
        self.epoch = 0
        self.difficulty_history: List[float] = []

    def _compute_progress(self) -> float:
        if self.epoch <= self.warmup_epochs:
            return 0.0
        remaining = max(1, self.max_epochs - self.warmup_epochs)
        progress = (self.epoch - self.warmup_epochs) / remaining
        return max(0.0, min(1.0, progress))

    def step(self) -> float:
        self.epoch += 1
        progress = self._compute_progress()
        if self.schedule == "linear":
            self.current_difficulty = self.start_difficulty + progress * (self.end_difficulty - self.start_difficulty)
        elif self.schedule == "exponential":
            if self.start_difficulty == 0:
                self.current_difficulty = self.end_difficulty * progress
            else:
                self.current_difficulty = self.start_difficulty * (self.end_difficulty / self.start_difficulty) ** progress
        elif self.schedule == "root":
            self.current_difficulty = self.start_difficulty + (self.end_difficulty - self.start_difficulty) * (progress ** 0.5)
        elif self.schedule == "step":
            steps = 5
            self.current_difficulty = self.start_difficulty + (self.end_difficulty - self.start_difficulty) * (math.floor(progress * steps) / steps)
        else:
            self.current_difficulty = self.end_difficulty
        self.difficulty_history.append(self.current_difficulty)
        return self.current_difficulty

    def filter_samples(self, samples: List[float], difficulty_scores: List[float]) -> Tuple[List[float], List[float]]:
        filtered_samples = []
        filtered_difficulties = []
        for sample, score in zip(samples, difficulty_scores):
            if score <= self.current_difficulty:
                filtered_samples.append(sample)
                filtered_difficulties.append(score)
        return filtered_samples, filtered_difficulties

    def get_difficulty_report(self) -> Dict[str, float]:
        return {
            "epoch": float(self.epoch),
            "current_difficulty": self.current_difficulty,
            "schedule": self.schedule,
            "history_length": float(len(self.difficulty_history)),
        }

    def reset(self) -> None:
        self.current_difficulty = self.start_difficulty
        self.epoch = 0
        self.difficulty_history.clear()
