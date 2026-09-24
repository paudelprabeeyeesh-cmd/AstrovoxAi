import math
from typing import List, Tuple


class RobustClassifier:
    def __init__(self, num_classes: int, l2_alpha: float = 0.1, noise_std: float = 0.05) -> None:
        if num_classes < 1:
            raise ValueError("num_classes must be positive")
        self._num_classes = num_classes
        self._l2_alpha = l2_alpha
        self._noise_std = noise_std
        self._weights: List[List[float]] = []
        self._trained: bool = False

    def _add_noise(self, values: List[float]) -> List[float]:
        noise = [math.fabs(values[i]) * self._noise_std * math.cos(math.pi * values[i]) for i in range(len(values))]
        return [v + n for v, n in zip(values, noise)]

    def train(self, inputs: List[List[float]], labels: List[int]) -> None:
        if not inputs or not labels:
            raise ValueError("training data must not be empty")
        if len(inputs) != len(labels):
            raise ValueError("inputs and labels must have the same length")
        if any(label >= self._num_classes for label in labels):
            raise ValueError("label out of range")
        if not self._weights:
            self._weights = [[0.0] * len(inputs[0]) for _ in range(self._num_classes)]
        for sample, label in zip(inputs, labels):
            noisy = self._add_noise(sample)
            for cls_idx in range(self._num_classes):
                gradient = noisy if cls_idx == label else [-v for v in noisy]
                for feat in range(len(noisy)):
                    self._weights[cls_idx][feat] -= self._l2_alpha * gradient[feat]
        self._trained = True

    def predict(self, sample: List[float]) -> int:
        if not self._trained or not self._weights:
            raise RuntimeError("train() before predict()")
        scores = [sum(w * f for w, f in zip(ws, sample)) for ws in self._weights]
        return max(range(self._num_classes), key=lambda i: scores[i])

    def evaluate(self, inputs: List[List[float]], labels: List[int]) -> float:
        if not inputs or not labels:
            raise ValueError("evaluation data must not be empty")
        if len(inputs) != len(labels):
            raise ValueError("inputs and labels must have the same length")
        correct = sum(1 for sample, label in zip(inputs, labels) if self.predict(sample) == label)
        return correct / len(inputs)

    def robustness_score(self, sample: List[float]) -> float:
        if not self._trained or not self._weights:
            raise RuntimeError("train() before robustness_score()")
        scores = [sum(w * f for w, f in zip(ws, sample)) for ws in self._weights]
        top = max(scores)
        rest = sorted(scores, reverse=True)[1] if len(scores) > 1 else 0.0
        return (top - rest) / (math.fabs(top) + 1e-8)
