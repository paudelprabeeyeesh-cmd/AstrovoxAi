import math


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _vsub(a, b):
    return [ai - bi for ai, bi in zip(a, b)]


def _vadd(a, b):
    return [ai + bi for ai, bi in zip(a, b)]


def _vscalar_mul(s, v):
    return [s * vi for vi in v]


def ista(f, grad_f, prox, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = list(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        x_new = prox(_vadd(x, _vscalar_mul(-lr, g)), lr)
        if _norm(_vsub(x_new, x)) < tol:
            break
        x = x_new
    return x
