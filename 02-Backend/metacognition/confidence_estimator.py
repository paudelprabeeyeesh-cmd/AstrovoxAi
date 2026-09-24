import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ConfidenceEstimate:
    score: float
    variance: float
    sample_count: int
    dimensions: Dict[str, float]


class ConfidenceEstimator:
    def __init__(self, min_samples: int = 1, prior_strength: float = 1.0):
        self.min_samples = min_samples
        self.prior_strength = prior_strength
        self.history: Dict[str, List[float]] = {}
        self.dimensions: Dict[str, Dict[str, List[float]]] = {}

    def record_sample(self, key: str, score: float, dimension: Optional[str] = None) -> None:
        if key not in self.history:
            self.history[key] = []
        self.history[key].append(score)
        if dimension is not None:
            if key not in self.dimensions:
                self.dimensions[key] = {}
            if dimension not in self.dimensions[key]:
                self.dimensions[key][dimension] = []
            self.dimensions[key][dimension].append(score)

    def estimate(self, key: str) -> ConfidenceEstimate:
        samples = self.history.get(key, [])
        sample_count = len(samples)
        if sample_count == 0:
            return ConfidenceEstimate(score=0.5, variance=0.25, sample_count=0, dimensions={})
        avg = sum(samples) / sample_count
        if sample_count > 1:
            variance = sum((s - avg) ** 2 for s in samples) / (sample_count - 1)
        else:
            variance = 0.25
        dim_scores = {}
        for dim, vals in self.dimensions.get(key, {}).items():
            if vals:
                dim_scores[dim] = sum(vals) / len(vals)
        return ConfidenceEstimate(score=avg, variance=variance, sample_count=sample_count, dimensions=dim_scores)

    def bayesian_estimate(self, key: str, prior: float = 0.5) -> ConfidenceEstimate:
        samples = self.history.get(key, [])
        sample_count = len(samples)
        if sample_count == 0:
            return ConfidenceEstimate(score=prior, variance=self._prior_variance(), sample_count=0, dimensions={})
        avg = sum(samples) / sample_count
        effective_strength = self.prior_strength
        n = sample_count + effective_strength
        posterior = (avg * sample_count + prior * effective_strength) / n
        if sample_count > 1:
            variance = sum((s - avg) ** 2 for s in samples) / sample_count
        else:
            variance = 0.25
        variance = variance / n + self._prior_variance() / effective_strength
        dim_scores = {}
        for dim, vals in self.dimensions.get(key, {}).items():
            if vals:
                dim_scores[dim] = sum(vals) / len(vals)
        return ConfidenceEstimate(score=posterior, variance=variance, sample_count=sample_count, dimensions=dim_scores)

    def calibration_error(self, key: str, accuracy: float) -> float:
        est = self.estimate(key)
        return abs(est.score - accuracy)

    def _prior_variance(self) -> float:
        return 0.25

    def reliability(self, key: str) -> float:
        est = self.estimate(key)
        if est.sample_count < self.min_samples:
            return 0.0
        return max(0.0, 1.0 - math.sqrt(est.variance))

    def confidence_interval(self, key: str, z: float = 1.96) -> Dict[str, float]:
        est = self.estimate(key)
        if est.sample_count == 0:
            return {"lower": 0.0, "upper": 1.0}
        std = math.sqrt(est.variance)
        margin = z * std / math.sqrt(est.sample_count)
        return {"lower": max(0.0, est.score - margin), "upper": min(1.0, est.score + margin)}
