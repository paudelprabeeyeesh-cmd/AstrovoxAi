from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class RegularizationConfig:
    l2_lambda: float = 0.01
    ewc_lambda: float = 100.0
    si_lambda: float = 1.0
    dropout_rate: float = 0.0


class ParameterRegularization:
    def __init__(self, config: Optional[RegularizationConfig] = None):
        self.config = config or RegularizationConfig()
        self.optimal_params: Dict[str, List[float]] = {}
        self.fisher: Dict[str, List[float]] = {}
        self.si_importance: Dict[str, List[float]] = {}
        self.task_optimal: Dict[int, Dict[str, List[float]]] = {}
        self.task_fisher: Dict[int, Dict[str, List[float]]] = {}
        self.regularization_history: List[Dict[str, float]] = []

    def set_optimal_params(self, params: Dict[str, List[float]]) -> None:
        self.optimal_params = {k: list(v) for k, v in params.items()}

    def compute_fisher(self, params: Dict[str, List[float]], gradients: Dict[str, List[float]]) -> None:
        self.fisher = {k: [g ** 2 for g in gradients[k]] for k in gradients if k in params}

    def compute_si_importance(
        self,
        current_params: Dict[str, List[float]],
        old_params: Dict[str, List[float]],
    ) -> None:
        self.si_importance = {}
        for name in current_params:
            if name in old_params and len(current_params[name]) == len(old_params[name]):
                imp = []
                for c, o in zip(current_params[name], old_params[name]):
                    delta = c - o
                    imp.append(1.0 / (delta ** 2 + 1e-4) if abs(delta) > 1e-4 else 0.0)
                self.si_importance[name] = imp

    def l2_penalty(self, current_params: Dict[str, List[float]]) -> float:
        penalty = 0.0
        for name, values in current_params.items():
            if name in self.optimal_params:
                penalty += sum((v - o) ** 2 for v, o in zip(values, self.optimal_params[name]))
        return self.config.l2_lambda * penalty

    def ewc_penalty(self, current_params: Dict[str, List[float]]) -> float:
        loss = 0.0
        for name, values in current_params.items():
            if name in self.fisher and name in self.optimal_params:
                loss += sum(
                    f * (v - o) ** 2
                    for f, v, o in zip(self.fisher[name], values, self.optimal_params[name])
                )
        return 0.5 * self.config.ewc_lambda * loss

    def si_penalty(self, current_params: Dict[str, List[float]]) -> float:
        loss = 0.0
        for name, values in current_params.items():
            if name in self.si_importance and name in self.optimal_params:
                loss += sum(
                    imp * (v - o) ** 2
                    for imp, v, o in zip(self.si_importance[name], values, self.optimal_params[name])
                )
        return 0.5 * self.config.si_lambda * loss

    def combined_penalty(self, current_params: Dict[str, List[float]]) -> float:
        return self.l2_penalty(current_params) + self.ewc_penalty(current_params) + self.si_penalty(current_params)

    def consolidate_task(self, task_id: int, params: Dict[str, List[float]]) -> None:
        self.task_optimal[task_id] = {k: list(v) for k, v in params.items()}
        self.task_fisher[task_id] = {k: list(v) for k, v in self.fisher.items()}

    def get_task_regularization(self, task_id: int, current_params: Dict[str, List[float]]) -> Dict[str, float]:
        opt = self.task_optimal.get(task_id, {})
        fish = self.task_fisher.get(task_id, {})
        l2 = 0.0
        ewc = 0.0
        for name, values in current_params.items():
            if name in opt:
                l2 += sum((v - o) ** 2 for v, o in zip(values, opt[name]))
            if name in fish and name in opt:
                ewc += sum(f * (v - o) ** 2 for f, v, o in zip(fish[name], values, opt[name]))
        return {
            "l2_penalty": self.config.l2_lambda * l2,
            "ewc_penalty": 0.5 * self.config.ewc_lambda * ewc,
            "total": self.config.l2_lambda * l2 + 0.5 * self.config.ewc_lambda * ewc,
        }

    def regularization_report(self) -> Dict[str, float]:
        if not self.regularization_history:
            return {"avg_l2": 0.0, "avg_ewc": 0.0, "avg_total": 0.0, "steps": 0.0}
        avg_l2 = sum(r["l2_penalty"] for r in self.regularization_history) / len(self.regularization_history)
        avg_ewc = sum(r["ewc_penalty"] for r in self.regularization_history) / len(self.regularization_history)
        avg_total = sum(r["total"] for r in self.regularization_history) / len(self.regularization_history)
        return {"avg_l2": avg_l2, "avg_ewc": avg_ewc, "avg_total": avg_total, "steps": float(len(self.regularization_history))}
