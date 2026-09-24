import math


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(_dot(a, a))


def _add(a, b):
    return [x + y for x, y in zip(a, b)]


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _scalar_mul(s, a):
    return [s * x for x in a]


def lbfgs(f, grad, x0, max_iter=100, tol=1e-6, m=10):
    x = list(x0)
    s_store = []
    y_store = []
    g = list(grad(x))
    for _ in range(max_iter):
        if _norm(g) < tol:
            break
        q = list(g)
        alphas = []
        for s, y in zip(reversed(s_store), reversed(y_store)):
            alphas.append(_dot(s, q) / (_dot(y, s) + 1e-10))
            q = _sub(q, _scalar_mul(alphas[-1], y))
        if s_store:
            gamma = _dot(s_store[-1], s_store[-1]) / (_dot(s_store[-1], y_store[-1]) + 1e-10)
        else:
            gamma = 1.0
        r = _scalar_mul(gamma, q)
        for alpha, s, y in zip(reversed(alphas), s_store, y_store):
            beta = _dot(y, r) / (_dot(y, s) + 1e-10)
            r = _add(r, _scalar_mul(alpha - beta, s))
        p = _scalar_mul(-1.0, r)
        step = list(p)
        alpha_ls = 1.0
        fx = f(x)
        while f(_add(x, _scalar_mul(alpha_ls, step))) > fx + 1e-4 * alpha_ls * _dot(step, g):
            alpha_ls *= 0.5
            if alpha_ls < 1e-8:
                break
        x_new = _add(x, _scalar_mul(alpha_ls, step))
        s = _sub(x_new, x)
        y = _sub(list(grad(x_new)), g)
        s_store.append(s)
        y_store.append(y)
        if len(s_store) > m:
            s_store.pop(0)
            y_store.pop(0)
        x = x_new
        g = list(grad(x))
    return x
