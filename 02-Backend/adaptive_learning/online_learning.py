import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class OnlineLearner:
    def __init__(self, learning_rate: float = 0.001, window_size: int = 100):
        self.learning_rate = learning_rate
        self.window_size = window_size
        self.weights: Optional[np.ndarray] = None
        self.data_window: List[Tuple[np.ndarray, np.ndarray]] = []
        self.loss_window: List[float] = []
        self.step_count = 0
        self.drift_detected = False
        self.drift_points: List[int] = []

    def _init_weights(self, x: np.ndarray) -> None:
        if self.weights is None:
            self.weights = np.random.randn(x.shape[1], 1).astype(np.float64) * 0.01

    def partial_fit(self, x: np.ndarray, y: np.ndarray) -> float:
        x = np.atleast_2d(x)
        y = np.atleast_2d(y)
        self._init_weights(x)
        preds = x @ self.weights
        loss = float(np.mean((preds - y) ** 2))
        grad = (2.0 / len(x)) * (x.T @ (preds - y))
        self.weights -= self.learning_rate * grad
        self.step_count += 1
        for xi, yi in zip(x, y):
            self.data_window.append((xi, yi))
            self.loss_window.append(loss)
        if len(self.data_window) > self.window_size:
            self.data_window = self.data_window[-self.window_size:]
            self.loss_window = self.loss_window[-self.window_size:]
        self._check_drift()
        return loss

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.weights is None:
            return np.zeros((x.shape[0], 1), dtype=np.float64)
        return np.atleast_2d(x) @ self.weights

    def _check_drift(self) -> None:
        if len(self.loss_window) < self.window_size // 2:
            return
        recent = np.array(self.loss_window[-self.window_size // 2:])
        older = np.array(self.loss_window[: -self.window_size // 2]) if len(self.loss_window) > self.window_size // 2 else recent
        mean_recent = np.mean(recent)
        mean_older = np.mean(older)
        std_recent = np.std(recent) + 1e-12
        z_score = abs(mean_recent - mean_older) / std_recent
        if z_score > 2.0:
            self.drift_detected = True
            self.drift_points.append(self.step_count)
        else:
            self.drift_detected = False

    def get_drift_report(self) -> Dict[str, Any]:
        return {
            "drift_detected": self.drift_detected,
            "drift_points": self.drift_points,
            "step_count": self.step_count,
            "window_utilization": len(self.data_window) / max(self.window_size, 1),
        }
