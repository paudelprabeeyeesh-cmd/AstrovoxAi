import math


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(_dot(a, a))


def _add(a, b):
    return [x + y for x, y in zip(a, b)]


def _scalar_mul(s, a):
    return [s * x for x in a]


def natural_gradient_step(params, grad, fisher_diag, step_size=0.1):
    nat_grad = [g / (f + 1e-8) for g, f in zip(grad(params), fisher_diag(params))]
    return _add(params, _scalar_mul(-step_size, nat_grad))


def natural_gradient_descent(f, grad, fisher_diag, x0, max_iter=100, tol=1e-6, step_size=0.1):
    x = list(x0)
    for _ in range(max_iter):
        g = grad(x)
        if _norm(g) < tol:
            break
        x = natural_gradient_step(x, grad, fisher_diag, step_size)
    return x
