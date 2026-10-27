"""AstrovoxAI Mathematics Module

Core mathematical primitives for the AI system:
- Linear algebra (vectors, matrices, dot product, matrix multiplication,
  norms, transpose, inverse, identity, trace, determinant)
- Gradients (numerical gradient, partial derivatives, gradient descent,
  MSE loss and gradient)
- Calculus (derivatives via central differences)
- Statistics (mean, variance, std, covariance, Pearson correlation)

All functions are pure Python (stdlib only), deterministic, and dependency-free
so they are safe for production AI code paths.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Union

Number = Union[int, float]
Vector = List[float]
Matrix = List[List[float]]


# ---------------------------------------------------------------------------
# Vector operations
# ---------------------------------------------------------------------------

def vector_add(a: Vector, b: Vector) -> Vector:
    """Element-wise addition of two vectors."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    return [x + y for x, y in zip(a, b)]


def vector_sub(a: Vector, b: Vector) -> Vector:
    """Element-wise subtraction of two vectors."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    return [x - y for x, y in zip(a, b)]


def vector_scale(scalar: Number, v: Vector) -> Vector:
    """Multiply every component of a vector by a scalar."""
    return [scalar * x for x in v]


def vector_dot(a: Vector, b: Vector) -> float:
    """Dot (scalar) product of two vectors."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    return sum(x * y for x, y in zip(a, b))


def vector_norm(v: Vector, order: int = 2) -> float:
    """Lp norm of a vector (default L2 / Euclidean norm)."""
    if order == 1:
        return sum(abs(x) for x in v)
    if order == 2:
        return math.sqrt(sum(x * x for x in v))
    if order == math.inf:
        return max(abs(x) for x in v) if v else 0.0
    return math.pow(sum(abs(x) ** order for x in v), 1.0 / order)


def vector_normalize(v: Vector) -> Vector:
    """Return the unit vector in the same direction (L2 normalized)."""
    n = vector_norm(v, 2)
    if n == 0:
        raise ValueError("cannot normalize the zero vector")
    return [x / n for x in v]


def vector_distance(a: Vector, b: Vector) -> float:
    """Euclidean distance between two vectors."""
    return vector_norm(vector_sub(a, b), 2)


def vector_cosine_similarity(a: Vector, b: Vector) -> float:
    """Cosine similarity between two vectors in [-1, 1]."""
    na = vector_norm(a, 2)
    nb = vector_norm(b, 2)
    if na == 0 or nb == 0:
        raise ValueError("cannot compute similarity with a zero vector")
    return vector_dot(a, b) / (na * nb)


# ---------------------------------------------------------------------------
# Matrix operations
# ---------------------------------------------------------------------------

def matrix_shape(m: Matrix) -> tuple[int, int]:
    """Return (rows, cols) of a matrix."""
    if not m or not m[0]:
        return (0, 0)
    return (len(m), len(m[0]))


def matrix_add(a: Matrix, b: Matrix) -> Matrix:
    """Element-wise addition of two matrices."""
    ra, ca = matrix_shape(a)
    rb, cb = matrix_shape(b)
    if (ra, ca) != (rb, cb):
        raise ValueError("matrices must have the same shape")
    return [[a[i][j] + b[i][j] for j in range(ca)] for i in range(ra)]


def matrix_scale(scalar: Number, m: Matrix) -> Matrix:
    """Multiply every entry of a matrix by a scalar."""
    rows, cols = matrix_shape(m)
    return [[scalar * m[i][j] for j in range(cols)] for i in range(rows)]


def matrix_mul(a: Matrix, b: Matrix) -> Matrix:
    """Matrix-matrix product (a @ b)."""
    ra, ca = matrix_shape(a)
    rb, cb = matrix_shape(b)
    if ca != rb:
        raise ValueError(f"inner dimensions mismatch: {ca} != {rb}")
    result: Matrix = [[0.0] * cb for _ in range(ra)]
    for i in range(ra):
        for k in range(ca):
            aik = a[i][k]
            if aik == 0:
                continue
            for j in range(cb):
                result[i][j] += aik * b[k][j]
    return result


def matrix_transpose(m: Matrix) -> Matrix:
    """Transpose of a matrix."""
    rows, cols = matrix_shape(m)
    return [[m[i][j] for i in range(rows)] for j in range(cols)]


def matrix_identity(n: int) -> Matrix:
    """n x n identity matrix."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def matrix_inverse_2x2(m: Matrix) -> Matrix:
    """Inverse of a 2x2 matrix. Raises on singular matrix."""
    if matrix_shape(m) != (2, 2):
        raise ValueError("only 2x2 matrices are supported")
    a, b = m[0]
    c, d = m[1]
    det = a * d - b * c
    if det == 0:
        raise ValueError("matrix is singular and cannot be inverted")
    return [[d / det, -b / det], [-c / det, a / det]]


def matrix_det_2x2(m: Matrix) -> float:
    """Determinant of a 2x2 matrix."""
    if matrix_shape(m) != (2, 2):
        raise ValueError("only 2x2 matrices are supported")
    return m[0][0] * m[1][1] - m[0][1] * m[1][0]


def matrix_trace(m: Matrix) -> float:
    """Trace (sum of diagonal) of a square matrix."""
    rows, cols = matrix_shape(m)
    if rows != cols:
        raise ValueError("trace requires a square matrix")
    return sum(m[i][i] for i in range(rows))


# ---------------------------------------------------------------------------
# Gradients / calculus
# ---------------------------------------------------------------------------

def numerical_gradient(f, x: Vector, eps: float = 1e-6) -> Vector:
    """Numerical gradient of f at x using central differences."""
    grad: Vector = []
    for i in range(len(x)):
        x_plus = list(x)
        x_minus = list(x)
        x_plus[i] += eps
        x_minus[i] -= eps
        grad.append((f(x_plus) - f(x_minus)) / (2 * eps))
    return grad


def partial_derivative(f, var_index: int, x: Vector, eps: float = 1e-6) -> float:
    """Partial derivative of f with respect to variable at var_index."""
    x_plus = list(x)
    x_minus = list(x)
    x_plus[var_index] += eps
    x_minus[var_index] -= eps
    return (f(x_plus) - f(x_minus)) / (2 * eps)


def gradient_descent_step(
    params: Vector,
    gradient: Vector,
    learning_rate: float = 0.01,
) -> Vector:
    """Single gradient descent update: params -= lr * gradient."""
    return vector_sub(params, vector_scale(learning_rate, gradient))


def mean_squared_error(y_true: Vector, y_pred: Vector) -> float:
    """Mean squared error between true and predicted values."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    n = len(y_true)
    return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / n


def mse_gradient(y_true: Vector, y_pred: Vector) -> Vector:
    """Gradient of MSE with respect to y_pred."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    n = len(y_true)
    return [2 * (p - t) / n for t, p in zip(y_true, y_pred)]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def mean(values: Sequence[Number]) -> float:
    """Arithmetic mean."""
    if not values:
        raise ValueError("cannot compute mean of empty sequence")
    return sum(values) / len(values)


def variance(values: Sequence[Number], ddof: int = 0) -> float:
    """Sample/population variance (ddof=1 for sample)."""
    n = len(values)
    if n == 0:
        raise ValueError("cannot compute variance of empty sequence")
    if n - ddof <= 0:
        raise ValueError("ddof too large for sample size")
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (n - ddof)


def std(values: Sequence[Number], ddof: int = 0) -> float:
    """Standard deviation."""
    return math.sqrt(variance(values, ddof))


def covariance(x: Sequence[Number], y: Sequence[Number]) -> float:
    """Covariance between two sequences."""
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    n = len(x)
    if n < 2:
        raise ValueError("need at least two points")
    mx, my = mean(x), mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (n - 1)


def pearson_correlation(x: Sequence[Number], y: Sequence[Number]) -> float:
    """Pearson correlation coefficient in [-1, 1]."""
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    n = len(x)
    if n < 2:
        raise ValueError("need at least two points")
    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = sum((a - mx) ** 2 for a in x)
    dy = sum((b - my) ** 2 for b in y)
    if dx == 0 or dy == 0:
        raise ValueError("cannot correlate with zero-variance input")
    return num / math.sqrt(dx * dy)


__all__ = [
    "vector_add",
    "vector_sub",
    "vector_scale",
    "vector_dot",
    "vector_norm",
    "vector_normalize",
    "vector_distance",
    "vector_cosine_similarity",
    "matrix_shape",
    "matrix_add",
    "matrix_scale",
    "matrix_mul",
    "matrix_transpose",
    "matrix_identity",
    "matrix_inverse_2x2",
    "matrix_det_2x2",
    "matrix_trace",
    "numerical_gradient",
    "partial_derivative",
    "gradient_descent_step",
    "mean_squared_error",
    "mse_gradient",
    "mean",
    "variance",
    "std",
    "covariance",
    "pearson_correlation",
]
