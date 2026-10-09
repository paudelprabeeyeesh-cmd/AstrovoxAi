import math


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _vsub(a, b):
    return [ai - bi for ai, bi in zip(a, b)]


def alternating_projection(proj_a, proj_b, x0, max_iter=1000, tol=1e-6):
    x = list(x0)
    for _ in range(max_iter):
        x_new = proj_b(proj_a(x))
        if _norm(_vsub(x_new, x)) < tol:
            break
        x = x_new
    return x
