import math


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _vsub(a, b):
    return [ai - bi for ai, bi in zip(a, b)]


def _vadd(a, b):
    return [ai + bi for ai, bi in zip(a, b)]


def _vscalar_mul(s, v):
    return [s * vi for vi in v]


def douglas_rachford(prox_a, prox_b, x0, max_iter=1000, tol=1e-6):
    x = list(x0)
    for _ in range(max_iter):
        y = _vsub(_vscalar_mul(2.0, prox_a(x, 1.0)), x)
        x_new = _vsub(_vscalar_mul(2.0, prox_b(y, 1.0)), y)
        if _norm(_vsub(x_new, x)) < tol:
            break
        x = x_new
    return x
