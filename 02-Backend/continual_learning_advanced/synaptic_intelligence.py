from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SIState:
    param_values: Dict[str, float]
    omega: Dict[str, float] = field(default_factory=dict)
    importance: Dict[str, float] = field(default_factory=dict)


class SynapticIntelligence:
    def __init__(self, epsilon: float = 1e-3, damping: float = 1e-4):
        self.epsilon = epsilon
        self.damping = damping
        self.old_params: Dict[str, float] = {}
        self.omega: Dict[str, float] = {}
        self.importance: Dict[str, float] = {}
        self.grad_history: Dict[str, List[float]] = {}
        self.task_states: Dict[str, SIState] = {}

    def register_params(self, params: Dict[str, float]) -> None:
        for name in params:
            if name not in self.omega:
                self.omega[name] = 0.0
                self.importance[name] = 0.0
                self.grad_history[name] = []

    def record_step(self, params: Dict[str, float], grads: Dict[str, float]) -> None:
        if not self.old_params:
            self.old_params = dict(params)
            return
        for name in params:
            if name not in self.old_params:
                continue
            delta = params[name] - self.old_params[name]
            if abs(delta) > self.epsilon:
                g = grads.get(name, 0.0)
                self.omega[name] = self.omega.get(name, 0.0) + g / (delta ** 2 + self.damping)
                self.grad_history[name].append(g)
        self.old_params = dict(params)

    def compute_importance(self, params: Dict[str, float]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for name in params:
            omega_val = self.omega.get(name, 0.0)
            if name in self.old_params:
                delta = params[name] - self.old_params[name]
            else:
                delta = 0.0
            denom = delta ** 2 + self.epsilon
            result[name] = omega_val / denom if denom > self.epsilon else omega_val
        self.importance = result
        return result

    def penalty(self, current_params: Dict[str, float]) -> float:
        loss = 0.0
        for name, value in current_params.items():
            imp = self.importance.get(name, 0.0)
            if name in self.old_params:
                diff = value - self.old_params[name]
                loss += 0.5 * imp * (diff ** 2)
        return loss

    def consolidate_task(self, task_id: str, params: Dict[str, float]) -> None:
        self.task_states[task_id] = SIState(
            param_values=dict(params),
            omega=dict(self.omega),
            importance=dict(self.importance),
        )

    def get_task_importance(self, task_id: str) -> Dict[str, float]:
        if task_id not in self.task_states:
            return {}
        return dict(self.task_states[task_id].importance)
