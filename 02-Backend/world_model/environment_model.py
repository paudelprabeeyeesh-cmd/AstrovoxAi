from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class EnvironmentState:
    entities: Dict[str, np.ndarray] = field(default_factory=dict)
    properties: Dict[str, Dict[str, float]] = field(default_factory=dict)
    time_step: int = 0


@dataclass
class DynamicsModel:
    transition_matrix: np.ndarray
    noise_covariance: np.ndarray


class EnvironmentModel:
    def __init__(self, state_dim: int = 4, action_dim: int = 2):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.state = np.zeros(state_dim)
        self.dynamics = DynamicsModel(
            transition_matrix=np.eye(state_dim) + 0.01 * np.random.randn(state_dim, state_dim),
            noise_covariance=0.01 * np.eye(state_dim),
        )
        self.history: List[EnvironmentState] = []
        self.learned_transitions: List[Tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    def set_state(self, state: np.ndarray) -> None:
        self.state = np.array(state, dtype=float)
        self._snapshot()

    def step(self, action: np.ndarray = None) -> np.ndarray:
        action = action if action is not None else np.zeros(self.action_dim)
        noise = np.random.multivariate_normal(np.zeros(self.state_dim), self.dynamics.noise_covariance)
        self.state = self.dynamics.transition_matrix @ self.state + noise[:self.state_dim]
        self._snapshot()
        return self.state.copy()

    def _snapshot(self) -> None:
        snapshot = EnvironmentState(
            entities={"env": self.state.copy()},
            properties={"time_step": {"t": float(self.state.shape[0])}},
            time_step=len(self.history),
        )
        self.history.append(snapshot)

    def learn_transition(self, prev_state: np.ndarray, action: np.ndarray, next_state: np.ndarray) -> None:
        self.learned_transitions.append((prev_state.copy(), action.copy(), next_state.copy()))
        if len(self.learned_transitions) >= 2:
            states = np.array([t[0] for t in self.learned_transitions])
            nexts = np.array([t[2] for t in self.learned_transitions])
            if states.shape[0] > 1 and states.shape[1] == self.state_dim:
                cov = np.cov(states.T) + 1e-6 * np.eye(self.state_dim)
                try:
                    self.dynamics.noise_covariance = cov
                except np.linalg.LinAlgError:
                    pass

    def predict(self, horizon: int = 5, actions: List[np.ndarray] = None) -> np.ndarray:
        state = self.state.copy()
        predictions = [state.copy()]
        for t in range(horizon):
            action = actions[t] if actions and t < len(actions) else np.zeros(self.action_dim)
            noise = np.random.multivariate_normal(np.zeros(self.state_dim), self.dynamics.noise_covariance)
            state = self.dynamics.transition_matrix @ state + noise[:self.state_dim]
            predictions.append(state.copy())
        return np.array(predictions)

    def dynamics_uncertainty(self) -> float:
        return float(np.trace(self.dynamics.noise_covariance))
