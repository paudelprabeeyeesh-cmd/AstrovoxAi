import math
from typing import List, Tuple


class AdversarialDetector:
    def __init__(self, threshold: float = 0.3, max_norm: float = 1.5) -> None:
        self._threshold = threshold
        self._max_norm = max_norm
        self._baseline_norm: float = 0.0
        self._fitted: bool = False

    def fit(self, samples: List[List[float]]) -> None:
        if not samples:
            raise ValueError("samples must not be empty")
        self._baseline_norm = max(
            math.sqrt(sum(v * v for v in sample)) for sample in samples
        )
        self._fitted = True

    def l2_norm(self, vector: List[float]) -> float:
        return math.sqrt(sum(v * v for v in vector))

    def detect(self, data: List[float]) -> Tuple[bool, float]:
        if not self._fitted:
            raise RuntimeError("call fit() before detect()")
        norm = self.l2_norm(data)
        baseline = self._baseline_norm if self._baseline_norm > 1e-8 else 1.0
        score = norm / baseline
        return score > self._threshold or norm > self._max_norm, score

    def batch_detect(self, batch: List[List[float]]) -> List[Tuple[bool, float]]:
        return [self.detect(sample) for sample in batch]

    def is_adversarial(self, data: List[float]) -> bool:
        is_adversarial, _ = self.detect(data)
        return is_adversarial
