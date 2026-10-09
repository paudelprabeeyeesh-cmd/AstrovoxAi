import itertools
import numpy as np
from typing import Dict, Optional


def _info(system: np.ndarray, partition: np.ndarray) -> float:
    left = partition == 0
    right = partition == 1
    if not left.any() or not right.any():
        return 0.0
    joint = system.astype(float)
    p = joint / joint.sum()
    p_l = p[left].sum()
    p_r = p[right].sum()
    if p_l == 0 or p_r == 0:
        return 0.0
    p_l_given = p[left] / p_l
    p_r_given = p[right] / p_r
    return float(np.sum(p * np.log(p_l_given * p_l + p_r_given * p_r + 1e-12)))


def _min_info_partition(system: np.ndarray) -> float:
    n = system.size
    min_info = float("inf")
    best_phi = 0.0
    for partition in itertools.product([0, 1], repeat=n):
        partition = np.array(partition)
        if not (partition == 0).any() or not (partition == 1).any():
            continue
        info = _info(system, partition)
        if info < min_info:
            min_info = info
            best_phi = min_info
    return float(best_phi)


class SystemModel:
    def __init__(self, states: int, transition_matrix: Optional[np.ndarray] = None):
        self.states = int(states)
        if transition_matrix is None:
            transition_matrix = np.ones((states, states)) / (states * states)
        self.transition_matrix = np.array(transition_matrix, dtype=float)
        row_sums = self.transition_matrix.sum(axis=1, keepdims=True)
        np.divide(self.transition_matrix, row_sums, out=self.transition_matrix, where=row_sums != 0)

    def transition(self, state: np.ndarray) -> np.ndarray:
        return self.transition_matrix @ state

    def step(self, state: np.ndarray, steps: int = 1) -> np.ndarray:
        s = state.astype(float)
        s /= s.sum()
        for _ in range(steps):
            s = self.transition(s)
        return s

    def stationary(self, max_iter: int = 200, tol: float = 1e-8) -> np.ndarray:
        s = np.ones(self.states) / self.states
        for _ in range(max_iter):
            ns = self.transition(s)
            if np.linalg.norm(ns - s) < tol:
                break
            s = ns
        return s

    def cause_effect_structure(self, mechanism: np.ndarray) -> Dict[str, float]:
        mask = np.array(mechanism, dtype=bool)
        if not mask.any():
            return {"cause": 0.0, "effect": 0.0}
        effect_states = self.transition_matrix @ np.eye(self.states)[mask].sum(axis=0)
        cause_states = np.linalg.matrix_power(self.transition_matrix, 2).T @ np.eye(self.states)[mask].sum(axis=0)
        return {"cause": float(np.mean(cause_states)), "effect": float(np.mean(effect_states))}

    def integrated_information(self) -> float:
        system = self.stationary().reshape(1, -1)
        if system.sum() == 0:
            return 0.0
        system = system.ravel()
        return _min_info_partition(system)


def compute_phi(system: SystemModel) -> float:
    return float(system.integrated_information())
