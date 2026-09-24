from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class EWCConfig:
    lambda_val: float = 100.0
    sample_size: int = 100


class ElasticWeightConsolidation:
    def __init__(self, config: Optional[EWCConfig] = None) -> None:
        self.config = config if config is not None else EWCConfig()
        self.fisher: Dict[str, np.ndarray] = {}
        self.prev_params: Dict[str, np.ndarray] = {}
        self._param_shapes: Dict[str, tuple] = {}

    def register_params(self, params: Dict[str, np.ndarray]) -> None:
        for name, value in params.items():
            self._param_shapes[name] = value.shape
            self.fisher[name] = np.zeros_like(value, dtype=np.float64)

    def compute_fisher(self, params: Dict[str, np.ndarray], x: np.ndarray, forward_fn) -> None:
        self.register_params(params)
        n = min(self.config.sample_size, len(x))
        indices = np.arange(n)
        for idx in indices:
            xi = x[idx : idx + 1]
            logits = forward_fn(xi, params)
            target_logits = forward_fn(xi, self.prev_params) if self.prev_params else logits
            grad_output = 2.0 * (logits - target_logits) / xi.shape[0]
            for name in params:
                if name not in self._param_shapes:
                    continue
                grad_param = np.zeros_like(params[name], dtype=np.float64)
                if name == "W1":
                    h = np.maximum(xi @ params["W1"] + params["b1"], 0)
                    dh = grad_output @ params["W2"].T
                    dh = dh * (h > 0)
                    grad_param = xi.T @ dh
                elif name == "b1":
                    h = np.maximum(xi @ params["W1"] + params["b1"], 0)
                    dh = grad_output @ params["W2"].T
                    dh = dh * (h > 0)
                    grad_param = np.sum(dh, axis=0)
                elif name == "W2":
                    h = np.maximum(xi @ params["W1"] + params["b1"], 0)
                    grad_param = h.T @ grad_output
                elif name == "b2":
                    grad_param = np.sum(grad_output, axis=0)
                self.fisher[name] += grad_param ** 2
        for name in self.fisher:
            self.fisher[name] = np.clip(self.fisher[name] / n, 1e-10, None)

    def update_prev_params(self, params: Dict[str, np.ndarray]) -> None:
        self.prev_params = {k: v.copy() for k, v in params.items()}

    def penalty(self, params: Dict[str, np.ndarray]) -> float:
        penalty = 0.0
        for name in params:
            if name in self.fisher and name in self.prev_params:
                diff = params[name] - self.prev_params[name]
                penalty += float(np.sum(self.fisher[name] * (diff ** 2)))
        return 0.5 * self.config.lambda_val * penalty

    def get_report(self) -> Dict[str, Any]:
        return {
            "lambda": self.config.lambda_val,
            "num_params": len(self.fisher),
            "fisher_norms": {k: float(np.sum(v)) for k, v in self.fisher.items()},
        }
