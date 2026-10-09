import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


@dataclass
class DisentanglementConfig:
    latent_dim: int
    n_factors: int = 5
    n_samples_per_factor: int = 100


class DisentanglementMetrics:
    def __init__(self, config: DisentanglementConfig):
        self.config = config

    def beta_vae_score(self, latents: np.ndarray, factors: np.ndarray) -> float:
        if latents.shape[0] != factors.shape[0]:
            raise ValueError("latents and factors must have the same number of samples")
        scores = []
        for d in range(self.config.latent_dim):
            z = latents[:, d]
            group_variances = []
            for f in range(factors.shape[1]):
                values = np.unique(factors[:, f])
                if len(values) < 2:
                    continue
                group_means = np.array([z[factors[:, f] == v].mean() for v in values])
                group_variances.append(np.var(group_means))
            if not group_variances:
                scores.append(0.0)
            else:
                scores.append(np.mean(group_variances))
        return float(np.mean(scores)) if scores else 0.0

    def factor_vae_score(self, latents: np.ndarray, factors: np.ndarray) -> float:
        if latents.shape[0] != factors.shape[0]:
            raise ValueError("latents and factors must have the same number of samples")
        scores = []
        for d in range(self.config.latent_dim):
            z = latents[:, d]
            total_var = np.var(z)
            if total_var == 0:
                scores.append(0.0)
                continue
            explained = []
            for f in range(factors.shape[1]):
                values = np.unique(factors[:, f])
                if len(values) < 2:
                    continue
                group_means = np.array([z[factors[:, f] == v].mean() for v in values])
                explained.append(np.var(group_means))
            scores.append(float(np.mean(explained)) / float(total_var) if explained else 0.0)
        return float(np.mean(scores)) if scores else 0.0

    def mutual_information_gap(self, latents: np.ndarray, factors: np.ndarray) -> float:
        if latents.shape[0] != factors.shape[0]:
            raise ValueError("latents and factors must have the same number of samples")
        gaps = []
        for f in range(factors.shape[1]):
            z = latents
            values = np.unique(factors[:, f])
            if len(values) < 2:
                continue
            mutuals = []
            for d in range(self.config.latent_dim):
                zd = z[:, d]
                mi = 0.0
                for v in values:
                    mask = factors[:, f] == v
                    if mask.sum() == 0:
                        continue
                    p = mask.mean()
                    mi += p * np.var(zd[mask])
                mutuals.append(mi)
            if len(mutuals) >= 2:
                sorted_mi = sorted(mutuals, reverse=True)
                gaps.append(float(sorted_mi[0] - sorted_mi[1]))
        return float(np.mean(gaps)) if gaps else 0.0

    def evaluate(self, latents: np.ndarray, factors: np.ndarray) -> Dict[str, Any]:
        return {
            "beta_vae_score": self.beta_vae_score(latents, factors),
            "factor_vae_score": self.factor_vae_score(latents, factors),
            "mig": self.mutual_information_gap(latents, factors),
        }

    def get_report(self) -> Dict[str, Any]:
        return {
            "latent_dim": self.config.latent_dim,
            "n_factors": self.config.n_factors,
            "n_samples_per_factor": self.config.n_samples_per_factor,
        }
