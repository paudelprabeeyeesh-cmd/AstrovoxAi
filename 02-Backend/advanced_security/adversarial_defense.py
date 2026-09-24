import math
import random
from typing import List, Optional


class AdversarialTrainer:
    def __init__(self, epsilon: float = 0.1, step_size: float = 0.01, iterations: int = 1) -> None:
        self._epsilon = epsilon
        self._step_size = step_size
        self._iterations = iterations

    def fgsm(self, weights: List[float], loss_grad: List[float]) -> List[float]:
        perturb = [g / (math.sqrt(sum(gi * gi for gi in loss_grad)) + 1e-8) for g in loss_grad]
        return [w + self._epsilon * p for w, p in zip(weights, perturb)]

    def pgd(self, weights: List[float], loss_grad: List[float]) -> List[float]:
        current = weights[:]
        for _ in range(self._iterations):
            current = self.fgsm(current, loss_grad)
            clipped = [max(w - self._epsilon, min(w + self._epsilon, c)) for w, c in zip(weights, current)]
            current = clipped
        return current


class AdversarialDefense:
    def __init__(self) -> None:
        self._noise_std: float = 0.1

    def gaussian_noise(self, data: List[float]) -> List[float]:
        return [x + random.gauss(0, self._noise_std) for x in data]

    def gradient_pruning(self, gradients: List[float], threshold: float) -> List[float]:
        return [0.0 if abs(g) < threshold else g for g in gradients]

    def detect_outlier(self, weights: List[float], std_threshold: float = 3.0) -> List[int]:
        n = len(weights)
        mean = sum(weights) / n
        var = sum((w - mean) ** 2 for w in weights) / n
        std = math.sqrt(var) + 1e-8
        return [i for i, w in enumerate(weights) if abs(w - mean) > std_threshold * std]


class RandomizedSmoothing:
    def __init__(self, sigma: float = 0.5, num_samples: int = 32) -> None:
        self._sigma = sigma
        self._num_samples = num_samples

    def smooth(self, weights: List[float], samples: Optional[List[List[float]]] = None) -> List[float]:
        samples = samples or [self._augment(weights) for _ in range(self._num_samples)]
        length = len(weights)
        return [sum(s[i] for s in samples) / len(samples) for i in range(length)]

    def _augment(self, weights: List[float]) -> List[float]:
        return [x + random.gauss(0, self._sigma) for x in weights]


class LabelSmoothing:
    def __init__(self, smoothing: float = 0.1) -> None:
        self._smoothing = smoothing

    def apply(self, probs: List[float]) -> List[float]:
        return [(1 - self._smoothing) * p + self._smoothing / len(probs) for p in probs]
