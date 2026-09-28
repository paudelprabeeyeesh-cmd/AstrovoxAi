"""Omega-7: Scaling laws research for LLM training at multiple scales."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScalingLawConfig:
    N: int = 1_000_000_000
    D: int = 200_000_000_000
    C: float = 3.4e29
    a: float = 0.34
    b: float = 0.28
    c: float = 0.53
    alpha: float = 0.27
    beta: float = 0.24
    L_min: float = 1.69


class KaplanScalingLaw:
    def __init__(self, config: ScalingLawConfig | None = None):
        self.config = config or ScalingLawConfig()

    def compute_loss(self, N: int, D: int) -> float:
        C = self.config.C
        a = self.config.a
        b = self.config.b
        return C / (N ** a) + C / (D ** b)

    def optimal_N(self, D: int) -> int:
        a, b = self.config.a, self.config.b
        return int((a / b) ** (1 / (a + b)) * D ** (b / (a + b)))

    def optimal_D(self, N: int) -> int:
        a, b = self.config.a, self.config.b
        return int((b / a) ** (1 / (a + b)) * N ** (a / (a + b)))


class ChinchillaScalingLaw:
    def __init__(self, config: ScalingLawConfig | None = None):
        self.config = config or ScalingLawConfig()

    def compute_loss(self, N: int, D: int) -> float:
        E = self.config.L_min + (self.config.C / (N ** self.config.alpha)) + (self.config.C / (D ** self.config.beta))
        return E

    def optimal_N(self, D: int) -> int:
        alpha, beta = self.config.alpha, self.config.beta
        return int((alpha / beta) ** (1 / (alpha + beta)) * D ** (beta / (alpha + beta)))

    def optimal_D(self, N: int) -> int:
        alpha, beta = self.config.alpha, self.config.beta
        return int((beta / alpha) ** (1 / (alpha + beta)) * N ** (alpha / (alpha + beta)))


class ParamEfficiencyScaling:
    @staticmethod
    def compute_efficiency(N: int, D: int, loss: float) -> float:
        C_est = loss * (N ** 0.34) * (D ** 0.28)
        return C_est


class ScalingResearch:
    def __init__(self, config: ScalingLawConfig | None = None):
        self.config = config or ScalingLawConfig()
        self.kaplan = KaplanScalingLaw(config)
        self.chinchilla = ChinchillaScalingLaw(config)

    def compare_laws(self, model_sizes: list[int], dataset_sizes: list[int]) -> dict[str, Any]:
        results = {"kaplan": [], "chinchilla": []}
        for N in model_sizes:
            for D in dataset_sizes:
                results["kaplan"].append({
                    "N": N,
                    "D": D,
                    "loss": self.kaplan.compute_loss(N, D),
                    "optimal_N": self.kaplan.optimal_N(D),
                    "optimal_D": self.kaplan.optimal_D(N),
                })
                results["chinchilla"].append({
                    "N": N,
                    "D": D,
                    "loss": self.chinchilla.compute_loss(N, D),
                    "optimal_N": self.chinchilla.optimal_N(D),
                    "optimal_D": self.chinchilla.optimal_D(N),
                })
        return results

    def fit_scaling_law(self, observed: list[dict[str, float]]) -> dict[str, float]:
        import numpy as np
        N = np.array([o["N"] for o in observed])
        D = np.array([o["D"] for o in observed])
        L = np.array([o["loss"] for o in observed])
        log_N = np.log(N)
        log_D = np.log(D)
        log_L = np.log(L)
        A = np.vstack([np.ones_like(log_N), log_N, log_D]).T
        coeffs, *_ = np.linalg.lstsq(A, log_L, rcond=None)
        return {"intercept": float(coeffs[0]), "alpha": float(coeffs[1]), "beta": float(coeffs[2])}
