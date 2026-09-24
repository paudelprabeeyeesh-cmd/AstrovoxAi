import math
from typing import Any, Dict, Tuple

from dataclasses import dataclass, field


@dataclass
class OptimizerState:
    t: int = 0
    m: Dict[str, float] = field(default_factory=dict)
    v: Dict[str, float] = field(default_factory=dict)


class MetaOptimizer:
    def __init__(
        self,
        params: Dict[str, float],
        lr: float = 1e-3,
        betas: Tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
    ):
        self.params = {k: float(v) for k, v in params.items()}
        self.lr = float(lr)
        self.betas = tuple(betas)
        self.eps = float(eps)
        self.state = OptimizerState()
        self.state.m = {k: 0.0 for k in self.params}
        self.state.v = {k: 0.0 for k in self.params}
        self.grads: Dict[str, float] = {k: 0.0 for k in self.params}

    def zero_grad(self) -> None:
        for k in self.grads:
            self.grads[k] = 0.0

    def add_grad(self, grads: Dict[str, float]) -> None:
        for k, g in grads.items():
            if k in self.grads:
                self.grads[k] += float(g)

    def step(self) -> None:
        self.state.t += 1
        beta1, beta2 = self.betas
        for k in self.params:
            g = self.grads[k]
            self.state.m[k] = beta1 * self.state.m[k] + (1 - beta1) * g
            self.state.v[k] = beta2 * self.state.v[k] + (1 - beta2) * (g ** 2)
            m_hat = self.state.m[k] / (1 - beta1 ** self.state.t)
            v_hat = self.state.v[k] / (1 - beta2 ** self.state.t)
            self.params[k] -= self.lr * m_hat / (math.sqrt(v_hat) + self.eps)

    def get_params(self) -> Dict[str, float]:
        return dict(self.params)

    def state_dict(self) -> Dict[str, Any]:
        return {
            "t": self.state.t,
            "m": dict(self.state.m),
            "v": dict(self.state.v),
        }
