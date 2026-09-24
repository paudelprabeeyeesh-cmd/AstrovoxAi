import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class CurriculumConfig:
    start_difficulty: float = 0.1
    end_difficulty: float = 1.0
    schedule: str = "linear"
    warmup_epochs: int = 5


class CurriculumScheduler:
    def __init__(self, config: Optional[CurriculumConfig] = None):
        self.config = config or CurriculumConfig()
        self.current_difficulty = self.config.start_difficulty
        self.epoch = 0
        self.difficulty_history: List[float] = []

    def step(self) -> float:
        self.epoch += 1
        if self.epoch <= self.config.warmup_epochs:
            self.current_difficulty = self.config.start_difficulty
        else:
            progress = min((self.epoch - self.config.warmup_epochs) / max(1, 50 - self.config.warmup_epochs), 1.0)
            if self.config.schedule == "linear":
                self.current_difficulty = self.config.start_difficulty + progress * (self.config.end_difficulty - self.config.start_difficulty)
            elif self.config.schedule == "exponential":
                self.current_difficulty = self.config.start_difficulty * (self.config.end_difficulty / self.config.start_difficulty) ** progress
            else:
                self.current_difficulty = self.config.end_difficulty
        self.difficulty_history.append(self.current_difficulty)
        return self.current_difficulty

    def filter_samples(self, x: np.ndarray, y: np.ndarray, difficulty_scores: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mask = difficulty_scores <= self.current_difficulty
        return x[mask], y[mask]

    def get_difficulty_report(self) -> Dict[str, Any]:
        return {
            "epoch": self.epoch,
            "current_difficulty": self.current_difficulty,
            "schedule": self.config.schedule,
            "history": self.difficulty_history,
        }


class KnowledgeDistiller:
    def __init__(self, temperature: float = 2.0):
        self.temperature = temperature
        self.teacher_logits: List[np.ndarray] = []
        self.student_logits: List[np.ndarray] = []

    def distill(self, teacher_logits: np.ndarray, student_logits: np.ndarray, targets: Optional[np.ndarray] = None) -> float:
        soft_targets = self._softmax(teacher_logits / self.temperature)
        student_soft = self._softmax(student_logits / self.temperature)
        kd_loss = -np.mean(np.sum(soft_targets * np.log(student_soft + 1e-12), axis=1))
        if targets is not None:
            hard_loss = -np.mean(np.log(student_soft[np.arange(len(targets)), targets.astype(int)] + 1e-12))
            total_loss = kd_loss + hard_loss
        else:
            total_loss = kd_loss
        self.teacher_logits.append(teacher_logits)
        self.student_logits.append(student_logits)
        return float(total_loss)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def get_distillation_stats(self) -> Dict[str, Any]:
        return {
            "num_distillations": len(self.teacher_logits),
            "temperature": self.temperature,
        }
