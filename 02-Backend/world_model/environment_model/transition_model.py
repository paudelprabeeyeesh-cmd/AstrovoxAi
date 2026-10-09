from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import random
import math


@dataclass
class DynamicsModel:
    transition_matrix: List[List[float]] = field(default_factory=list)
    noise_covariance: List[List[float]] = field(default_factory=list)


class TransitionModel:
    def __init__(self, state_dim: int = 4) -> None:
        self.state_dim = state_dim
        self.transition_matrix = [
            [1.0 if i == j else 0.0 for j in range(state_dim)] for i in range(state_dim)
        ]
        for i in range(state_dim):
            self.transition_matrix[i][i] += 0.01 * (random.random() - 0.5) * 2.0
        self.noise_covariance = [
            [0.01 if i == j else 0.0 for j in range(state_dim)] for i in range(state_dim)
        ]
        self.learned_transitions: List[tuple] = []

    def _matmul(self, matrix: List[List[float]], vector: List[float]) -> List[float]:
        cols = len(matrix[0]) if matrix else 0
        return [
            sum(matrix[i][j] * vector[j] for j in range(cols))
            for i in range(len(matrix))
        ]

    def step(self, state: List[float], action: List[float]) -> List[float]:
        next_state = self._matmul(self.transition_matrix, state)
        for i in range(min(len(action), self.state_dim)):
            next_state[i] += action[i]
        noise = [
            random.gauss(0.0, math.sqrt(max(self.noise_covariance[i][i], 1e-12)))
            for i in range(self.state_dim)
        ]
        for i in range(self.state_dim):
            next_state[i] += noise[i]
        return next_state

    def update(self, prev_state: List[float], action: List[float], next_state: List[float]) -> None:
        self.learned_transitions.append((list(prev_state), list(action), list(next_state)))
        if len(self.learned_transitions) >= 2:
            states = [t[0] for t in self.learned_transitions]
            n = len(states)
            d = self.state_dim
            means = [sum(s[i] for s in states) / n for i in range(d)]
            cov = [[0.0] * d for _ in range(d)]
            for s in states:
                for i in range(d):
                    for j in range(d):
                        cov[i][j] += (s[i] - means[i]) * (s[j] - means[j])
            for i in range(d):
                for j in range(d):
                    cov[i][j] /= n
            for i in range(d):
                cov[i][i] += 1e-6
            self.noise_covariance = cov
