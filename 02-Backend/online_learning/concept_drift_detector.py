import math
from typing import List, Optional, Dict, Any


class ConceptDriftDetector:
    def __init__(self, window_size: int = 100, threshold: float = 2.0):
        self.window_size = window_size
        self.threshold = threshold
        self.values: List[float] = []
        self.drift_detected = False
        self.drift_points: List[int] = []
        self.step_count = 0

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _std(values: List[float]) -> float:
        if not values:
            return 0.0
        m = sum(values) / len(values)
        variance = sum((v - m) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    def update(self, value: float) -> Optional[bool]:
        self.values.append(value)
        self.step_count += 1
        if len(self.values) > self.window_size:
            self.values = self.values[-self.window_size:]
        return self._check_drift()

    def _check_drift(self) -> Optional[bool]:
        if len(self.values) < self.window_size // 2:
            return None
        half = self.window_size // 2
        recent = self.values[-half:]
        older = self.values[:-half] if len(self.values) > half else recent
        mean_recent = self._mean(recent)
        mean_older = self._mean(older)
        std_older = self._std(older) + 1e-12
        z_score = abs(mean_recent - mean_older) / std_older
        if z_score > self.threshold:
            self.drift_detected = True
            self.drift_points.append(self.step_count)
            return True
        self.drift_detected = False
        return False

    def get_report(self) -> Dict[str, Any]:
        return {
            "drift_detected": self.drift_detected,
            "drift_points": list(self.drift_points),
            "step_count": self.step_count,
            "window_size": self.window_size,
            "window_utilization": len(self.values) / max(self.window_size, 1),
        }
