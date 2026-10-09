import numpy as np
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class ExplorationStep:
    state: np.ndarray
    action: int
    risk_score: float
    allowed: bool
    reward: float


@dataclass
class SafetyConstraint:
    name: str
    threshold: float
    fn: Callable


class SafeExplorer:
    def __init__(self, state_dim: int, num_actions: int, risk_threshold: float = 0.3):
        self.state_dim = state_dim
        self.num_actions = num_actions
        self.risk_threshold = risk_threshold
        self.constraints: List[SafetyConstraint] = []
        self.exploration_history: List[ExplorationStep] = []
        rng = np.random.RandomState(42)
        self.q_table = rng.randn(state_dim, num_actions) * 0.01

    def add_constraint(self, constraint: SafetyConstraint) -> None:
        self.constraints.append(constraint)

    def compute_risk(self, state: np.ndarray, action: int) -> float:
        risk = 0.0
        for constraint in self.constraints:
            val = float(constraint.fn(state))
            if val > constraint.threshold:
                risk += (val - constraint.threshold)
        q_values = self.q_table[state.astype(int) % len(self.q_table)]
        risk += float(np.std(q_values)) * 0.1
        return float(np.clip(risk, 0.0, 1.0))

    def select_action(self, state: np.ndarray, epsilon: float = 0.1) -> int:
        state_idx = int(np.mean(state)) % self.num_actions
        if np.random.rand() < epsilon:
            return int(np.random.randint(0, self.num_actions))
        return int(np.argmax(self.q_table[state_idx]))

    def explore(self, state: np.ndarray, epsilon: float = 0.1, transition_fn: Optional[Callable] = None) -> ExplorationStep:
        action = self.select_action(state, epsilon)
        risk = self.compute_risk(state, action)
        allowed = risk < self.risk_threshold
        if transition_fn is not None:
            transition_fn(state, action)
            reward = float(np.random.rand()) if allowed else -1.0
            state_idx = int(np.mean(state)) % self.q_table.shape[0]
            self.q_table[state_idx, action] += 0.1 * (reward - self.q_table[state_idx, action])
        else:
            state.copy()
            reward = 0.0
        step = ExplorationStep(
            state=state.copy(),
            action=action,
            risk_score=round(risk, 6),
            allowed=allowed,
            reward=round(reward, 6),
        )
        self.exploration_history.append(step)
        return step

    def get_exploration_stats(self) -> Dict:
        if not self.exploration_history:
            return {"total": 0, "allowed_rate": 0.0, "avg_risk": 0.0}
        total = len(self.exploration_history)
        allowed = sum(1 for s in self.exploration_history if s.allowed)
        avg_risk = np.mean([s.risk_score for s in self.exploration_history])
        return {
            "total": total,
            "allowed_rate": round(allowed / total, 4),
            "avg_risk": round(float(avg_risk), 4),
        }
