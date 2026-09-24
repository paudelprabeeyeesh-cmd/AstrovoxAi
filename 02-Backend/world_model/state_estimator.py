from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StateEstimate:
    state: List[float]
    covariance: List[List[float]]
    timestamp: float = 0.0


class StateEstimator:
    def __init__(self, state_dim: int = 4):
        self.state_dim = state_dim
        self.history: List[StateEstimate] = []
        self.estimate = StateEstimate(
            state=[0.0] * state_dim,
            covariance=[[1.0 if i == j else 0.0 for j in range(state_dim)] for i in range(state_dim)],
        )

    def update(self, measurement: List[float], measurement_noise: float = 0.1) -> StateEstimate:
        if len(measurement) != self.state_dim:
            raise ValueError(f"Measurement dimension {len(measurement)} != state dimension {self.state_dim}")
        new_state = [0.0] * self.state_dim
        for i in range(self.state_dim):
            new_state[i] = 0.5 * self.estimate.state[i] + 0.5 * measurement[i]
        new_cov = [[self.estimate.covariance[i][j] * 0.5 for j in range(self.state_dim)] for i in range(self.state_dim)]
        for i in range(self.state_dim):
            new_cov[i][i] += measurement_noise
        self.estimate = StateEstimate(state=new_state, covariance=new_cov, timestamp=len(self.history))
        self.history.append(self.estimate)
        return self.estimate

    def predict(self, steps: int = 5) -> List[StateEstimate]:
        predictions = []
        state = list(self.estimate.state)
        cov = [row[:] for row in self.estimate.covariance]
        for _ in range(steps):
            new_state = list(state)
            for i in range(self.state_dim):
                new_state[i] += 0.01 * state[i]
            new_cov = [[cov[i][j] + 0.01 for j in range(self.state_dim)] for i in range(self.state_dim)]
            estimate = StateEstimate(state=new_state, covariance=new_cov, timestamp=len(predictions))
            predictions.append(estimate)
            state = new_state
            cov = new_cov
        return predictions

    def uncertainty(self) -> float:
        if not self.history:
            return 1.0
        return sum(self.history[-1].covariance[i][i] for i in range(self.state_dim)) / self.state_dim

    def confidence(self) -> float:
        u = self.uncertainty()
        return max(0.0, min(1.0, 1.0 - u))
