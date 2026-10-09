from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ProgressConfig:
    window_size: int = 20
    plateau_threshold: float = 0.01


class ProgressEstimator:
    def __init__(self, config: Optional[ProgressConfig] = None):
        self.config = config or ProgressConfig()
        self.metrics: List[float] = []

    def update(self, metric: float) -> None:
        self.metrics.append(metric)
        if len(self.metrics) > self.config.window_size:
            self.metrics.pop(0)

    def get_progress(self) -> float:
        if len(self.metrics) < 2:
            return 0.0
        return self.metrics[-1] - self.metrics[0]

    def is_plateau(self) -> bool:
        if len(self.metrics) < self.config.window_size:
            return False
        recent = self.metrics[-self.config.window_size:]
        return max(recent) - min(recent) < self.config.plateau_threshold

    def get_estimate(self) -> Dict[str, Any]:
        if not self.metrics:
            return {"mean": 0.0, "trend": 0.0, "is_plateau": False}
        mean = sum(self.metrics) / len(self.metrics)
        trend = self.metrics[-1] - self.metrics[0] if len(self.metrics) > 1 else 0.0
        return {
            "mean": mean,
            "trend": trend,
            "is_plateau": self.is_plateau(),
            "count": len(self.metrics),
        }
