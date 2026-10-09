import math
from typing import List, Tuple


class CertifiedDefense:
    def __init__(self, sigma: float = 0.25, num_samples: int = 64, alpha: float = 0.01) -> None:
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        if num_samples < 1:
            raise ValueError("num_samples must be positive")
        self._sigma = sigma
        self._num_samples = num_samples
        self._alpha = alpha

    def _augment(self, vector: List[float]) -> List[float]:
        return [v + self._sigma * math.cos(math.pi * v) for v in vector]

    def smoothed_predict(self, weights: List[List[float]], sample: List[float]) -> int:
        votes = [0] * len(weights)
        for _ in range(self._num_samples):
            augmented = self._augment(sample)
            scores = [sum(w * f for w, f in zip(ws, augmented)) for ws in weights]
            predicted = max(range(len(weights)), key=lambda i: scores[i])
            votes[predicted] += 1
        return max(range(len(votes)), key=lambda i: votes[i])

    def certified_accuracy(self, weights: List[List[float]], samples: List[List[float]]) -> float:
        if not samples:
            return 0.0
        correct = sum(1 for sample in samples if self.smoothed_predict(weights, sample) == 0)
        return correct / len(samples)

    def radius(self, counts: List[int]) -> float:
        if not counts:
            raise ValueError("counts must not be empty")
        total = sum(counts)
        if total < 1:
            raise ValueError("counts must sum to at least 1")
        top = max(counts)
        p_top = top / total
        radius = self._sigma * math.sqrt(2 * math.log(1 / self._alpha))
        radius = radius + self._sigma * (p_top * math.log(p_top) + (1 - p_top) * math.log(1 - p_top + 1e-12))
        return math.fabs(radius)

    def certify(self, weights: List[List[float]], sample: List[float]) -> Tuple[int, float]:
        votes = [0] * len(weights)
        for _ in range(self._num_samples):
            augmented = self._augment(sample)
            scores = [sum(w * f for w, f in zip(ws, augmented)) for ws in weights]
            predicted = max(range(len(weights)), key=lambda i: scores[i])
            votes[predicted] += 1
        predicted = max(range(len(votes)), key=lambda i: votes[i])
        return predicted, self.radius(votes)

    def randomized_smoothing(self, sample: List[float]) -> List[float]:
        return [sum(self._augment(sample)[i] for _ in range(self._num_samples)) / self._num_samples for i in range(len(sample))]
