from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class ExplorationState:
    state_vector: np.ndarray
    visit_count: int = 0
    total_reward: float = 0.0
    last_visited: float = 0.0


class CuriosityDriven:
    def __init__(self, state_dim: int = 16, epsilon: float = 0.1, decay: float = 0.99):
        self.state_dim = state_dim
        self.epsilon = epsilon
        self.decay = decay
        self.state_bank: Dict[int, ExplorationState] = {}
        self.curiosity_scores: List[float] = []
        self._step = 0.0

    def _hash_state(self, state: np.ndarray) -> int:
        return int(np.sum(np.floor(state * 1000))) % (2**31)

    def compute_curiosity(self, state: np.ndarray, reward: float) -> Tuple[float, int]:
        key = self._hash_state(state)
        if key not in self.state_bank:
            self.state_bank[key] = ExplorationState(state_vector=state.copy(), last_visited=self._step)
        entry = self.state_bank[key]
        entry.visit_count += 1
        entry.total_reward += reward
        entry.last_visited = self._step
        novelty = 1.0 / (1.0 + entry.visit_count)
        curiosity = self.epsilon * novelty + (1.0 - self.epsilon) * abs(reward - entry.total_reward / entry.visit_count)
        curiosity = max(0.0, min(1.0, curiosity))
        self.curiosity_scores.append(curiosity)
        if len(self.curiosity_scores) > 1000:
            self.curiosity_scores.pop(0)
        return curiosity, key

    def select_action(self, state: np.ndarray, q_values: np.ndarray) -> int:
        curiosity, _ = self.compute_curiosity(state, 0.0)
        if np.random.random() < curiosity:
            return int(np.random.randint(0, len(q_values)))
        return int(np.argmax(q_values))

    def update_epsilon(self) -> None:
        self.epsilon = max(0.01, self.epsilon * self.decay)

    def get_state_novelty(self, state: np.ndarray) -> float:
        key = self._hash_state(state)
        entry = self.state_bank.get(key)
        if entry is None:
            return 1.0
        return 1.0 / (1.0 + entry.visit_count)

    def get_exploration_stats(self) -> Dict[str, Any]:
        if not self.curiosity_scores:
            return {"mean_curiosity": 0.0, "visited_states": len(self.state_bank)}
        return {
            "mean_curiosity": float(np.mean(self.curiosity_scores)),
            "std_curiosity": float(np.std(self.curiosity_scores)),
            "visited_states": len(self.state_bank),
            "epsilon": self.epsilon,
        }

    def decay_states(self, half_life: float = 100.0) -> None:
        self._step += 1.0
        to_remove = []
        for key, entry in self.state_bank.items():
            if self._step - entry.last_visited > half_life * 2:
                to_remove.append(key)
        for key in to_remove:
            del self.state_bank[key]
