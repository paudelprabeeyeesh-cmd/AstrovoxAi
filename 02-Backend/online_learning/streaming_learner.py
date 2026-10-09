import random
import math
from typing import List, Tuple, Optional, Dict, Any


class StreamingLearner:
    def __init__(self, learning_rate: float = 0.001, window_size: int = 100):
        self.learning_rate = learning_rate
        self.window_size = window_size
        self.weights: Optional[List[float]] = None
        self.data_window: List[Tuple[List[float], float]] = []
        self.loss_window: List[float] = []
        self.step_count = 0
        self.drift_detected = False
        self.drift_points: List[int] = []

    def _init_weights(self, x: List[float]) -> None:
        if self.weights is None:
            self.weights = [random.uniform(-0.01, 0.01) for _ in range(len(x))]

    @staticmethod
    def _dot(a: List[float], b: List[float]) -> float:
        return sum(ai * bi for ai, bi in zip(a, b))

    def partial_fit(self, x: List[float], y: float) -> float:
        x = list(x)
        self._init_weights(x)
        pred = self._dot(x, self.weights)
        loss = (pred - y) ** 2
        grad = [2.0 * xi * (pred - y) for xi in x]
        self.weights = [w - self.learning_rate * g for w, g in zip(self.weights, grad)]
        self.step_count += 1
        self.data_window.append((x, y))
        self.loss_window.append(loss)
        if len(self.data_window) > self.window_size:
            self.data_window = self.data_window[-self.window_size:]
            self.loss_window = self.loss_window[-self.window_size:]
        self._check_drift()
        return loss

    def predict(self, x: List[float]) -> float:
        if self.weights is None:
            return 0.0
        return self._dot(x, self.weights)

    def _mean(self, values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def _std(self, values: List[float]) -> float:
        if not values:
            return 0.0
        m = self._mean(values)
        variance = sum((v - m) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    def _check_drift(self) -> None:
        if len(self.loss_window) < self.window_size // 2:
            return
        half = self.window_size // 2
        recent = self.loss_window[-half:]
        older = self.loss_window[:-half] if len(self.loss_window) > half else recent
        mean_recent = self._mean(recent)
        mean_older = self._mean(older)
        std_recent = self._std(recent) + 1e-12
        z_score = abs(mean_recent - mean_older) / std_recent
        if z_score > 2.0:
            self.drift_detected = True
            self.drift_points.append(self.step_count)
        else:
            self.drift_detected = False

    def get_drift_report(self) -> Dict[str, Any]:
        return {
            "drift_detected": self.drift_detected,
            "drift_points": list(self.drift_points),
            "step_count": self.step_count,
            "window_utilization": len(self.data_window) / max(self.window_size, 1),
        }
