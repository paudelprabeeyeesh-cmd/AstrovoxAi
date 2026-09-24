import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class Synapse:
    weight: float
    last_update: float
    eligibility_trace: float = 0.0
    max_weight: float = 1.0
    min_weight: float = -1.0

    @classmethod
    def create(cls, weight: float, max_weight: float = 1.0, min_weight: float = -1.0) -> "Synapse":
        return cls(weight=weight, last_update=time.time(), max_weight=max_weight, min_weight=min_weight)

    def clip(self) -> None:
        self.weight = np.clip(self.weight, self.min_weight, self.max_weight)


class LearningRule:
    def __init__(self, learning_rate: float = 0.01):
        self.learning_rate = learning_rate
        self._update_history: List[Dict[str, Any]] = []

    def hebbian(self, pre: np.ndarray, post: np.ndarray, synapse: Synapse) -> float:
        delta = self.learning_rate * pre * post
        synapse.weight += float(np.mean(delta)) if delta.size > 0 else 0.0
        synapse.clip()
        synapse.last_update = time.time()
        self._update_history.append({
            "rule": "hebbian",
            "delta": float(np.mean(delta)) if delta.size > 0 else 0.0,
            "timestamp": synapse.last_update,
        })
        return float(np.mean(delta)) if delta.size > 0 else 0.0

    def stdp(self, pre: np.ndarray, post: np.ndarray, dt: np.ndarray, synapse: Synapse,
             tau_plus: float = 20.0, tau_minus: float = 20.0) -> float:
        dw = np.zeros_like(pre)
        for i in range(len(pre)):
            for j in range(len(post)):
                t_diff = dt[j] - dt[i]
                if t_diff > 0:
                    dw_j = self.learning_rate * np.exp(-t_diff / tau_plus)
                else:
                    dw_j = -self.learning_rate * np.exp(t_diff / tau_minus)
                synapse.weight += dw_j
        synapse.clip()
        synapse.last_update = time.time()
        delta = float(np.mean(dw)) if dw.size > 0 else 0.0
        self._update_history.append({
            "rule": "stdp",
            "delta": delta,
            "timestamp": synapse.last_update,
        })
        return delta

    def oja(self, pre: np.ndarray, post: np.ndarray, synapse: Synapse) -> float:
        delta = self.learning_rate * (post * (pre - synapse.weight * post))
        synapse.weight += float(np.mean(delta)) if delta.size > 0 else 0.0
        synapse.clip()
        synapse.last_update = time.time()
        self._update_history.append({
            "rule": "oja",
            "delta": float(np.mean(delta)) if delta.size > 0 else 0.0,
            "timestamp": synapse.last_update,
        })
        return float(np.mean(delta)) if delta.size > 0 else 0.0


class Metaplasticity:
    def __init__(self, sliding_threshold: float = 0.5, homeostatic_rate: float = 0.001):
        self.sliding_threshold = sliding_threshold
        self.homeostatic_rate = homeostatic_rate
        self._meta_history: List[Dict[str, Any]] = []

    def adjust_threshold(self, recent_activity: np.ndarray, current_threshold: float) -> float:
        avg_activity = float(np.mean(recent_activity)) if len(recent_activity) > 0 else 0.0
        if avg_activity > self.sliding_threshold:
            new_threshold = current_threshold + self.homeostatic_rate
        elif avg_activity < self.sliding_threshold:
            new_threshold = current_threshold - self.homeostatic_rate
        else:
            new_threshold = current_threshold
        self._meta_history.append({
            "avg_activity": avg_activity,
            "old_threshold": current_threshold,
            "new_threshold": new_threshold,
            "timestamp": time.time(),
        })
        return np.clip(new_threshold, 0.0, 1.0)

    def homeostatic_scaling(self, weights: List[Synapse], target_rate: float = 0.5) -> List[float]:
        total = sum(s.weight for s in weights)
        n = len(weights)
        if n == 0:
            return []
        current_rate = total / n
        scaling_factor = target_rate / current_rate if current_rate > 0 else 1.0
        adjustments = []
        for s in weights:
            old_w = s.weight
            s.weight *= scaling_factor
            s.clip()
            adjustments.append(s.weight - old_w)
        return adjustments


class NeuroplasticitySystem:
    def __init__(self, n_neurons_pre: int = 16, n_neurons_post: int = 16, learning_rate: float = 0.01):
        self.n_neurons_pre = n_neurons_pre
        self.n_neurons_post = n_neurons_post
        self.learning_rate = learning_rate
        self.synapses: List[List[Synapse]] = [
            [Synapse.create(weight=np.random.uniform(-0.1, 0.1)) for _ in range(n_neurons_post)]
            for _ in range(n_neurons_pre)
        ]
        self.learning_rule = LearningRule(learning_rate=learning_rate)
        self.metaplasticity = Metaplasticity()
        self._eligibility_decay: float = 0.01
        self._plasticity_log: List[Dict[str, Any]] = []

    def update(self, pre_activity: np.ndarray, post_activity: np.ndarray, rule: str = "hebbian") -> float:
        if pre_activity.shape[0] != self.n_neurons_pre or post_activity.shape[0] != self.n_neurons_post:
            raise ValueError("Activity dimensions mismatch")
        total_delta = 0.0
        for i in range(self.n_neurons_pre):
            for j in range(self.n_neurons_post):
                synapse = self.synapses[i][j]
                if rule == "hebbian":
                    delta = self.learning_rule.hebbian(
                        np.array([pre_activity[i]]), np.array([post_activity[j]]), synapse
                    )
                elif rule == "oja":
                    delta = self.learning_rule.oja(
                        np.array([pre_activity[i]]), np.array([post_activity[j]]), synapse
                    )
                else:
                    delta = self.learning_rule.hebbian(
                        np.array([pre_activity[i]]), np.array([post_activity[j]]), synapse
                    )
                synapse.eligibility_trace = synapse.eligibility_trace * (1.0 - self._eligibility_decay) + delta
                total_delta += abs(delta)
        self._plasticity_log.append({
            "rule": rule,
            "total_delta": total_delta,
            "timestamp": time.time(),
        })
        return total_delta

    def apply_stdp(self, pre_times: np.ndarray, post_times: np.ndarray) -> float:
        total_delta = 0.0
        for i in range(self.n_neurons_pre):
            for j in range(self.n_neurons_post):
                synapse = self.synapses[i][j]
                delta = self.learning_rule.stdp(
                    np.array([1.0]), np.array([1.0]), np.array([[pre_times[i] - post_times[j]]]), synapse
                )
                total_delta += abs(delta)
        return total_delta

    def homeostatic_scale(self, target_rate: float = 0.5) -> List[float]:
        all_synapses = [s for row in self.synapses for s in row]
        return self.metaplasticity.homeostatic_scaling(all_synapses, target_rate=target_rate)

    def get_weight_matrix(self) -> np.ndarray:
        return np.array([[s.weight for s in row] for row in self.synapses])

    def get_eligibility_matrix(self) -> np.ndarray:
        return np.array([[s.eligibility_trace for s in row] for row in self.synapses])
