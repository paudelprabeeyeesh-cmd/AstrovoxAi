from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DomainProfile:
    name: str
    feature_mean: List[float]
    feature_std: List[float]
    sample_count: int = 0


@dataclass
class AdaptationConfig:
    gamma: float = 0.01
    max_iterations: int = 100
    tolerance: float = 1e-6


class DomainAdapter:
    def __init__(self, source_domain: str, target_domain: str, config: Optional[AdaptationConfig] = None) -> None:
        self.source = DomainProfile(name=source_domain, feature_mean=[], feature_std=[])
        self.target = DomainProfile(name=target_domain, feature_mean=[], feature_std=[])
        self.config = config or AdaptationConfig()
        self.adaptation_log: List[Dict[str, Any]] = []
        self.adaptation_matrix: Optional[List[List[float]]] = None

    def fit(self, source_samples: List[List[float]], target_samples: List[List[float]]) -> None:
        if not source_samples or not target_samples:
            raise ValueError("source_samples and target_samples must be non-empty")
        source_dim = len(source_samples[0])
        target_dim = len(target_samples[0])
        if any(len(s) != source_dim for s in source_samples):
            raise ValueError("Inconsistent feature dimensions in source_samples")
        if any(len(s) != target_dim for s in target_samples):
            raise ValueError("Inconsistent feature dimensions in target_samples")
        self.source.feature_mean = self._compute_mean(source_samples)
        self.source.feature_std = self._compute_std(source_samples, self.source.feature_mean)
        self.target.feature_mean = self._compute_mean(target_samples)
        self.target.feature_std = self._compute_std(target_samples, self.target.feature_mean)
        self.source.sample_count = len(source_samples)
        self.target.sample_count = len(target_samples)
        self.adaptation_matrix = self._compute_adaptation_matrix(source_dim, target_dim)
        self.adaptation_log.append(
            {
                "action": "fit",
                "source_samples": self.source.sample_count,
                "target_samples": self.target.sample_count,
                "dim": source_dim,
            }
        )

    def _compute_mean(self, samples: List[List[float]]) -> List[float]:
        dim = len(samples[0])
        return [
            sum(sample[d] for sample in samples) / max(len(samples), 1)
            for d in range(dim)
        ]

    def _compute_std(self, samples: List[List[float]], mean: List[float]) -> List[float]:
        dim = len(samples[0])
        n = max(len(samples), 1)
        return [
            (sum((sample[d] - mean[d]) ** 2 for sample in samples) / n) ** 0.5
            for d in range(dim)
        ]

    def _compute_adaptation_matrix(self, source_dim: int, target_dim: int) -> List[List[float]]:
        if source_dim == target_dim:
            return [[1.0 if i == j else 0.0 for j in range(source_dim)] for i in range(source_dim)]
        min_dim = min(source_dim, target_dim)
        matrix: List[List[float]] = []
        for i in range(source_dim):
            row: List[float] = []
            for j in range(target_dim):
                if i == j and i < min_dim:
                    row.append(1.0)
                else:
                    row.append(0.0)
            matrix.append(row)
        return matrix

    def adapt(self, sample: List[float]) -> List[float]:
        if self.adaptation_matrix is None:
            raise RuntimeError("Adapter has not been fitted")
        if len(sample) != len(self.adaptation_matrix):
            raise ValueError("Sample dimension does not match adaptation matrix")
        adapted: List[float] = []
        for row in self.adaptation_matrix:
            val = sum(row[j] * sample[j] for j in range(len(row)))
            adapted.append(val)
        self.adaptation_log.append({"action": "adapt", "input_len": len(sample), "output_len": len(adapted)})
        return adapted

    def batch_adapt(self, samples: List[List[float]]) -> List[List[float]]:
        return [self.adapt(sample) for sample in samples]

    def summary(self) -> Dict[str, Any]:
        return {
            "source_domain": self.source.name,
            "target_domain": self.target.name,
            "source_samples": self.source.sample_count,
            "target_samples": self.target.sample_count,
            "fitted": self.adaptation_matrix is not None,
            "adaptation_steps": len(self.adaptation_log),
        }
