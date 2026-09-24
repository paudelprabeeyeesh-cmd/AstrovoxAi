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


def _matvecmul(M, v):
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _solve_linear(A, b):
    n = len(b)
    A = [row[:] for row in A]
    b = list(b)
    for i in range(n):
        pivot = A[i][i]
        if abs(pivot) < 1e-12:
            pivot = 1e-12
        for j in range(i, n):
            A[i][j] /= pivot
        b[i] /= pivot
        for k in range(i + 1, n):
            factor = A[k][i]
            for j in range(i, n):
                A[k][j] -= factor * A[i][j]
            b[k] -= factor * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = b[i] - sum(A[i][j] * x[j] for j in range(i + 1, n))
    return x


def trust_region_dogleg(grad_fn, hess_fn, x0, max_iter=100, tol=1e-6, radius=1.0):
    x = list(x0)
    for _ in range(max_iter):
        g = grad_fn(x)
        if _norm(g) < tol:
            break
        H = hess_fn(x)
        n = len(x)
        p_n = _solve_linear(H, [-gi for gi in g])
        gHg = _dot(g, _matvecmul(H, g))
        if gHg > 0:
            p_u = _scalar_mul(-(_dot(g, g) / gHg), g)
            if _norm(p_u) <= radius:
                p_c = list(p_u)
            else:
                p_c = _scalar_mul(-radius / _norm(g), g)
        else:
            p_c = _scalar_mul(-radius / _norm(g), g)
        if _norm(p_n) <= radius:
            p = list(p_n)
        else:
            p_c_norm = _norm(p_c)
            if p_c_norm >= radius:
                p = _scalar_mul(radius / p_c_norm, p_c)
            else:
                d = _sub(p_n, p_c)
                a_coeff = _dot(d, d)
                b_coeff = 2 * _dot(p_c, d)
                c_coeff = _dot(p_c, p_c) - radius * radius
                discriminant = b_coeff * b_coeff - 4 * a_coeff * c_coeff
                if discriminant < 0 or a_coeff == 0:
                    t = 0.0
                else:
                    sqrt_d = math.sqrt(discriminant)
                    t_candidates = [t for t in ((-b_coeff + sqrt_d) / (2 * a_coeff), (-b_coeff - sqrt_d) / (2 * a_coeff)) if 0 <= t <= 1]
                    t = min(t_candidates) if t_candidates else 0.0
                p = _add(p_c, _scalar_mul(t, d))
        x_new = _add(x, p)
        if _norm(_sub(x_new, x)) < tol:
            x = x_new
            break
        x = x_new
    return x
