import math


def _softmax_vector(vec: list[float], temperature: float) -> list[float]:
    max_val = max(vec)
    exps = [math.exp((v - max_val) / temperature) for v in vec]
    sum_exps = sum(exps)
    return [e / sum_exps for e in exps]


def _kl_divergence(p: list[float], q: list[float]) -> float:
    return sum(
        pi * math.log(pi / qi)
        for pi, qi in zip(p, q)
        if pi > 1e-12 and qi > 1e-12
    )


class ConsistencyRegularizer:
    def __init__(self, temperature: float = 1.0):
        self.temperature = temperature

    def __call__(self, logits1: list[list[float]], logits2: list[list[float]]) -> float:
        p1 = [_softmax_vector(row, self.temperature) for row in logits1]
        p2 = [_softmax_vector(row, self.temperature) for row in logits2]
        total = 0.0
        count = 0
        for row1, row2 in zip(p1, p2):
            total += _kl_divergence(row1, row2)
            count += 1
        return total / count if count else 0.0
