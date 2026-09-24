from typing import List, Optional, Tuple
import numpy as np


class StatePredictor:
    def __init__(self, state_dim: int = 4):
        self.state_dim = state_dim
        self.history: List[np.ndarray] = []

    def fit(self, states: List[np.ndarray]) -> None:
        self.history = [np.array(s, dtype=float) for s in states]
        if len(self.history) >= 2:
            self.A = np.eye(self.state_dim)
            self.Q = np.eye(self.state_dim) * 0.01
        else:
            self.A = np.eye(self.state_dim)
            self.Q = np.eye(self.state_dim) * 0.1

    def predict(self, horizon: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        if not self.history:
            state = np.zeros(self.state_dim)
            cov = np.eye(self.state_dim) * 1.0
        else:
            state = self.history[-1].copy()
            cov = np.eye(self.state_dim) * 0.1
        means = [state.copy()]
        variances = [np.trace(cov)]
        for _ in range(horizon):
            noise = np.random.multivariate_normal(np.zeros(self.state_dim), self.Q)
            state = self.A @ state + noise
            means.append(state.copy())
            variances.append(np.trace(cov))
        return np.array(means), np.array(variances)

    def uncertainty(self) -> float:
        if len(self.history) < 2:
            return 1.0
        recent = np.array(self.history[-10:])
        return float(np.mean(np.std(recent, axis=0)))

    def confidence(self) -> float:
        u = self.uncertainty()
        return max(0.0, min(1.0, 1.0 - u))


class TimeSeriesForecaster:
    def __init__(self, window: int = 5):
        self.window = window
        self.data: List[float] = []

    def add_point(self, value: float) -> None:
        self.data.append(value)

    def forecast(self, horizon: int = 3) -> Tuple[List[float], List[float]]:
        if len(self.data) < 2:
            mean = self.data[-1] if self.data else 0.0
            return [mean] * horizon, [1.0] * horizon
        window = self.data[-self.window:]
        mean = float(np.mean(window))
        std = float(np.std(window))
        return [mean] * horizon, [std] * horizon
