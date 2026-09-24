import math
from typing import List, Tuple, Callable


def _softmax_vector(vec: List[float], temperature: float) -> List[float]:
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
        model: Callable[[List[List[float]]], List[List[float]]],
        unlabeled_data: List[List[float]],
    ) -> Tuple[List[List[float]], List[int]]:
        logits = model(unlabeled_data)
        confident: List[List[float]] = []
        labels: List[int] = []
        for logit, sample in zip(logits, unlabeled_data):
            probs = _softmax_vector(logit, self.temperature)
            max_prob = max(probs)
            if max_prob >= self.threshold:
                label = probs.index(max_prob)
                confident.append(sample)
                labels.append(label)
        return confident, labels
