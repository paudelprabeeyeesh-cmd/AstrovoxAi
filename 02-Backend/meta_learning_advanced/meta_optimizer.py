import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class OptimizerState:
    t: int = 0
    m: Dict[str, np.ndarray] = field(default_factory=dict)
    v: Dict[str, np.ndarray] = field(default_factory=dict)


class MetaOptimizer:
    def __init__(self, params: Dict[str, np.ndarray], lr: float = 1e-3, betas: tuple = (0.9, 0.999), eps: float = 1e-8):
        self.params = {k: np.array(v, dtype=np.float64) for k, v in params.items()}
        self.lr = lr
        self.betas = betas
        self.eps = eps
        self.state = OptimizerState()
        self.state.m = {k: np.zeros_like(v) for k, v in self.params.items()}
        self.state.v = {k: np.zeros_like(v) for k, v in self.params.items()}
        self.grads: Dict[str, np.ndarray] = {k: np.zeros_like(v) for k, v in self.params.items()}

    def zero_grad(self) -> None:
        for k in self.grads:
            self.grads[k].fill(0.0)

    def add_grad(self, grads: Dict[str, np.ndarray]) -> None:
        for k, g in grads.items():
            if k in self.grads:
                self.grads[k] += g.astype(np.float64)

    def step(self) -> None:
        self.state.t += 1
        beta1, beta2 = self.betas
        for k in self.params:
            g = self.grads[k]
            self.state.m[k] = beta1 * self.state.m[k] + (1 - beta1) * g
            self.state.v[k] = beta2 * self.state.v[k] + (1 - beta2) * (g ** 2)
            m_hat = self.state.m[k] / (1 - beta1 ** self.state.t)
            v_hat = self.state.v[k] / (1 - beta2 ** self.state.t)
            self.params[k] -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)

    def get_params(self) -> Dict[str, np.ndarray]:
        return {k: np.array(v) for k, v in self.params.items()}

    def state_dict(self) -> Dict[str, Any]:
        return {
            't': self.state.t,
            'm': {k: v.copy() for k, v in self.state.m.items()},
            'v': {k: v.copy() for k, v in self.state.v.items()},
        }
