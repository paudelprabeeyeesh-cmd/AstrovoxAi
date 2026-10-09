import math
import random
from typing import Callable, List, Optional, Union


Number = Union[int, float]
Vector = List[Number]


def _norm(v: Vector) -> float:
    return math.sqrt(sum(x * x for x in v))


def stochastic_coordinate_descent(
    f: Callable[[Vector], Number],
    grad_f: Callable[[Vector], Vector],
    x0: Vector,
    lr: float = 1e-2,
    max_iter: int = 1000,
    tol: float = 1e-6,
    seed: Optional[int] = None,
) -> Vector:
    if seed is not None:
        random.seed(seed)
    x = list(x0)
    n = len(x)
    for _ in range(max_iter):
        i = random.randrange(n)
        g = grad_f(x)
        x[i] -= lr * g[i]
        if _norm(g) < tol:
            break
    return x
