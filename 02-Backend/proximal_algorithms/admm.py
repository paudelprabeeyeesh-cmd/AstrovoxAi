import math


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _vsub(a, b):
    return [ai - bi for ai, bi in zip(a, b)]


def _vadd(a, b):
    return [ai + bi for ai, bi in zip(a, b)]


def _vscalar_mul(s, v):
    return [s * vi for vi in v]


def admm(f, grad_f, prox, x0, z0, u0, rho=1.0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = list(x0)
    z = list(z0)
    u = list(u0)
    for _ in range(max_iter):
        g = _vadd(grad_f(x), _vscalar_mul(rho, _vadd(x, _vsub(u, z))))
        x = _vsub(x, _vscalar_mul(lr, g))
        z = prox(_vadd(z, u), 1.0 / rho)
        u = _vadd(u, _vsub(x, z))
        if _norm(_vsub(x, z)) < tol and _norm(u) < tol:
            break
    return x
