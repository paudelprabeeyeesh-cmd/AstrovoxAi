from __future__ import annotations
from typing import List, Optional
from .state_observer import EnvironmentState, StateObserver
from .transition_model import DynamicsModel, TransitionModel
from .reward_model import RewardModel


class EnvironmentModel:
    def __init__(self, state_dim: int = 4, action_dim: int = 2) -> None:
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.state: List[float] = [0.0] * state_dim
        self.dynamics = TransitionModel(state_dim=state_dim)
        self.observer = StateObserver()
        self.reward_model = RewardModel(weights=[-1.0] * state_dim)
        self.learned_transitions: List[tuple] = []

    @property
    def history(self):
        return self.observer.history

    def set_state(self, state: List[float]) -> None:
        self.state = list(state)
        self.observer.record(self.state)

    def step(self, action: Optional[List[float]] = None) -> List[float]:
        if action is None:
            action = [0.0] * self.action_dim
        self.state = self.dynamics.step(self.state, action)
        self.observer.record(self.state)
        return list(self.state)

    def learn_transition(self, prev_state: List[float], action: List[float], next_state: List[float]) -> None:
        self.learned_transitions.append((list(prev_state), list(action), list(next_state)))
        self.dynamics.update(prev_state, action, next_state)

    def predict(self, horizon: int = 5, actions: Optional[List[List[float]]] = None) -> List[List[float]]:
        state = list(self.state)
        predictions = [state]
        for t in range(horizon):
            action = actions[t] if actions and t < len(actions) else [0.0] * self.action_dim
            state = self.dynamics.step(state, action)
            predictions.append(list(state))
        return predictions

    def dynamics_uncertainty(self) -> float:
        trace = 0.0
        for i in range(self.state_dim):
            trace += self.dynamics.noise_covariance[i][i]
        return trace
