import math
from typing import Callable, List, Sequence, Union


Number = Union[int, float]
Vector = List[Number]


def _norm(v: Vector) -> float:
    return math.sqrt(sum(x * x for x in v))


def block_coordinate_descent(
    f: Callable[[Vector], Number],
    grad_f: Callable[[Vector], Vector],
    x0: Vector,
    blocks: Sequence[Sequence[int]],
    lr: float = 1e-2,
    max_iter: int = 1000,
    tol: float = 1e-6,
) -> Vector:
    x = list(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        for block in blocks:
            for idx in block:
                x[idx] -= lr * g[idx]
        if _norm(g) < tol:
            break
    return x
