import math
from enum import Enum
from typing import Callable, Dict, List, Optional


class ScheduleType(Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    ROOT = "root"
    STEP = "step"
    SIGMOID = "sigmoid"


def linear_pacing(progress: float) -> float:
    return progress


def exponential_pacing(progress: float, base: float = 2.0) -> float:
    return (base ** progress - 1.0) / (base - 1.0)


def root_pacing(progress: float, power: float = 2.0) -> float:
    return progress ** (1.0 / power)


def step_pacing(progress: float, steps: int = 5) -> float:
    return math.floor(progress * steps) / steps


def sigmoid_pacing(progress: float, steepness: float = 10.0) -> float:
    return 1.0 / (1.0 + math.exp(-steepness * (progress - 0.5)))


PACING_FUNCTIONS: Dict[ScheduleType, Callable[[float], float]] = {
    ScheduleType.LINEAR: linear_pacing,
    ScheduleType.EXPONENTIAL: exponential_pacing,
    ScheduleType.ROOT: root_pacing,
    ScheduleType.STEP: step_pacing,
    ScheduleType.SIGMOID: sigmoid_pacing,
}


class PacingFunction:
    def __init__(
        self,
        schedule_type: ScheduleType = ScheduleType.LINEAR,
        start_difficulty: float = 0.0,
        end_difficulty: float = 1.0,
        **kwargs: float,
    ):
        self.schedule_type = schedule_type
        self.start_difficulty = start_difficulty
        self.end_difficulty = end_difficulty
        self.params = kwargs
        self.func = PACING_FUNCTIONS[schedule_type]

    def get_difficulty(self, progress: float) -> float:
        progress = max(0.0, min(1.0, progress))
        pacing_value = self.func(progress, **self.params)
        return self.start_difficulty + pacing_value * (self.end_difficulty - self.start_difficulty)

    def get_difficulty_at_epoch(self, epoch: int, total_epochs: int) -> float:
        if total_epochs <= 1:
            return self.end_difficulty
        progress = (epoch - 1) / (total_epochs - 1)
        return self.get_difficulty(progress)

    def get_difficulty_curve(self, num_points: int = 100) -> List[float]:
        return [self.get_difficulty(i / (num_points - 1)) for i in range(num_points)]
