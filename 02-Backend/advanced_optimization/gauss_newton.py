import math


def _transpose(M):
    if not M:
        return []
    n = len(M)
    m = len(M[0])
    return [[M[i][j] for i in range(n)] for j in range(m)]


def _matmul(A, B):
    n = len(A)
    m = len(B[0])
    p = len(B)
    return [[sum(A[i][k] * B[k][j] for k in range(p)) for j in range(m)] for i in range(n)]


def _matvecmul(M, v):
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _add(a, b):
    return [x + y for x, y in zip(a, b)]


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


def gauss_newton(residual_fn, jacobian_fn, x0, max_iter=50, tol=1e-6):
    x = list(x0)
    for _ in range(max_iter):
        r = residual_fn(x)
        J = jacobian_fn(x)
        Jr = _matvecmul(_transpose(J), r)
        JtJ = _matmul(_transpose(J), J)
        p = _solve_linear(JtJ, [-ri for ri in Jr])
        x_new = _add(x, p)
        if math.sqrt(sum((xi - x[i]) ** 2 for i, xi in enumerate(x_new))) < tol:
            x = x_new
            break
        x = x_new
    return x
