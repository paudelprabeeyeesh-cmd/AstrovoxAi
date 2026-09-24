import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ScalingLawResult:
    optimal_params: float
    optimal_tokens: float
    optimal_flops: float
    chinchilla_loss: float
    compute_constrained_params: float


class ChinchillaScaling:
    def __init__(self, a: float = 1.5, b: float = 0.65, e: float = 2.0):
        self.a = a
        self.b = b
        self.e = e

    def loss(self, n: float, d: float) -> float:
        return self.e + (self.a / (n ** self.b)) + (self.a / (d ** self.b))

    def optimal_model_size(self, compute_budget: float) -> ScalingLawResult:
        n_opt = (compute_budget / (6 * self.a ** 2)) ** (1.0 / (self.b + 1.0))
        d_opt = compute_budget / (6 * n_opt)
        flops = 6 * n_opt * d_opt
        loss_val = self.loss(n_opt, d_opt)
        return ScalingLawResult(
            optimal_params=n_opt,
            optimal_tokens=d_opt,
            optimal_flops=flops,
            chinchilla_loss=loss_val,
            compute_constrained_params=n_opt,
        )

    def compute_optimal(self, compute_budget: float) -> Dict[str, float]:
        result = self.optimal_model_size(compute_budget)
        return {
            "optimal_params": result.optimal_params,
            "optimal_tokens": result.optimal_tokens,
            "optimal_flops": result.optimal_flops,
            "loss": result.chinchilla_loss,
        }

    def iso_compute_curve(self, compute_budget: float, num_points: int = 20) -> np.ndarray:
        opt_n = self.optimal_model_size(compute_budget).optimal_params
        log_lo = np.log10(opt_n) - 1.5
        log_hi = np.log10(opt_n) + 1.5
        ns = np.logspace(log_lo, log_hi, num_points)
        losses = []
        for n in ns:
            d = compute_budget / (6 * n)
            losses.append(self.loss(n, d))
        return np.array(losses)


class ScalingLawAnalyzer:
    def __init__(self, a: float = 1.5, b: float = 0.65, e: float = 2.0):
        self.scaling = ChinchillaScaling(a=a, b=b, e=e)

    def scaling_exponent_estimate(self, model_sizes: np.ndarray, losses: np.ndarray) -> float:
        log_n = np.log(model_sizes)
        log_e = np.log(losses - self.scaling.e)
        slope = np.polyfit(log_n, log_e, 1)[0]
        return float(-slope)

    def fit_chinchilla_params(self, n_values: np.ndarray, d_values: np.ndarray, loss_values: np.ndarray) -> Dict[str, float]:
        transformed = np.log(loss_values - self.scaling.e)
        A = np.column_stack([np.ones_like(transformed), -np.log(n_values), -np.log(d_values)])
        coeffs, _, _, _ = np.linalg.lstsq(A, transformed, rcond=None)
        return {"a": float(np.exp(coeffs[0])), "b": float(coeffs[1])}

    def predict_loss(self, n: float, d: float) -> float:
        return self.scaling.loss(n, d)

    def compute_efficient_frontier(self, compute_budgets: np.ndarray) -> Dict[str, np.ndarray]:
        params, tokens, losses = [], [], []
        for budget in compute_budgets:
            result = self.scaling.optimal_model_size(budget)
            params.append(result.optimal_params)
            tokens.append(result.optimal_tokens)
            losses.append(result.chinchilla_loss)
        return {"params": np.array(params), "tokens": np.array(tokens), "losses": np.array(losses)}
