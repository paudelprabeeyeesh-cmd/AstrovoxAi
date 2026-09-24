from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class RewardModel:
    weights: List[float] = field(default_factory=list)

    def compute(self, state: List[float], action: List[float]) -> float:
        reward = 0.0
        for i in range(min(len(self.weights), len(state))):
            reward += self.weights[i] * state[i]
        for i in range(min(len(self.weights), len(action))):
            reward -= 0.1 * (action[i] ** 2)
        return reward
