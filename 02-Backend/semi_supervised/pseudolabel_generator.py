import math
from collections.abc import Callable


def _softmax_vector(vec: list[float], temperature: float) -> list[float]:
    max_val = max(vec)
    exps = [math.exp((v - max_val) / temperature) for v in vec]
    sum_exps = sum(exps)
    return [e / sum_exps for e in exps]


class PseudolabelGenerator:
    def __init__(self, threshold: float = 0.95, temperature: float = 1.0):
        self.threshold = threshold
        self.temperature = temperature

    def generate(
        self,
        model: Callable[[list[list[float]]], list[list[float]]],
        unlabeled_data: list[list[float]],
    ) -> tuple[list[list[float]], list[int]]:
        logits = model(unlabeled_data)
        confident: list[list[float]] = []
        labels: list[int] = []
        for logit, sample in zip(logits, unlabeled_data):
            probs = _softmax_vector(logit, self.temperature)
            max_prob = max(probs)
            if max_prob >= self.threshold:
                label = probs.index(max_prob)
                confident.append(sample)
                labels.append(label)
        return confident, labels
