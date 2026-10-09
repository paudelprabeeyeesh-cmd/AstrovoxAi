import math
import random
from typing import List, Optional, Union


Number = Union[int, float]
Vector = List[Number]
Matrix = List[Vector]


def _dot(a: Vector, b: Vector) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def _norm(v: Vector) -> float:
    return math.sqrt(sum(x * x for x in v))


def randomized_kaczmarz(
    A: Matrix,
    b: Vector,
    x0: Optional[Vector] = None,
    max_iter: int = 1000,
    tol: float = 1e-6,
    seed: Optional[int] = None,
) -> Vector:
    if seed is not None:
        random.seed(seed)
    m = len(A)
    n = len(A[0]) if m > 0 else 0
    if x0 is None:
        x = [0.0] * n
    else:
        x = list(x0)

    for _ in range(max_iter):
        i = random.randrange(m)
        a_i = A[i]
        b_i = b[i]
        residual = b_i - _dot(a_i, x)
        norm_sq = _dot(a_i, a_i)
        if norm_sq == 0.0:
            continue
        coeff = residual / norm_sq
        for j in range(n):
            x[j] += coeff * a_i[j]

        residual_vec = [_dot(A[k], x) - b[k] for k in range(m)]
        if _norm(residual_vec) < tol:
            break
    return x
