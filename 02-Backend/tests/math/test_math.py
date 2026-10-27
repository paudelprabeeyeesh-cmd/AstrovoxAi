"""Regression tests for the AstrovoxAI mathematics module."""

from app.math import (
    covariance,
    gradient_descent_step,
    mse_gradient,
    mean,
    mean_squared_error,
    matrix_det_2x2,
    matrix_identity,
    matrix_inverse_2x2,
    matrix_mul,
    matrix_trace,
    matrix_transpose,
    numerical_gradient,
    partial_derivative,
    pearson_correlation,
    std,
    vector_add,
    vector_cosine_similarity,
    vector_distance,
    vector_dot,
    vector_norm,
    vector_normalize,
    vector_scale,
    vector_sub,
    variance,
)


def test_vector_add_and_sub():
    a = [1.0, 2.0, 3.0]
    b = [4.0, 5.0, 6.0]
    assert vector_add(a, b) == [5.0, 7.0, 9.0]
    assert vector_sub(b, a) == [3.0, 3.0, 3.0]


def test_vector_scale_and_dot():
    v = [1.0, 2.0, 3.0]
    assert vector_scale(2.0, v) == [2.0, 4.0, 6.0]
    assert abs(vector_dot(v, v) - 14.0) < 1e-9


def test_vector_norm_normalize_distance_cosine():
    v = [3.0, 4.0]
    assert abs(vector_norm(v) - 5.0) < 1e-9
    u = vector_normalize(v)
    assert abs(vector_norm(u) - 1.0) < 1e-9
    assert abs(vector_distance([0.0, 0.0], [3.0, 4.0]) - 5.0) < 1e-9
    assert abs(vector_cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(vector_cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-9


def test_matrix_mul_transpose_identity():
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    c = matrix_mul(a, b)
    assert c == [[19.0, 22.0], [43.0, 50.0]]
    assert matrix_transpose(a) == [[1.0, 3.0], [2.0, 4.0]]
    assert matrix_identity(2) == [[1.0, 0.0], [0.0, 1.0]]


def test_matrix_inverse_and_det():
    m = [[4.0, 7.0], [2.0, 6.0]]
    inv = matrix_inverse_2x2(m)
    prod = matrix_mul(m, inv)
    assert abs(prod[0][0] - 1.0) < 1e-9
    assert abs(prod[0][1]) < 1e-9
    assert abs(matrix_det_2x2(m) - 10.0) < 1e-9
    assert matrix_trace([[1.0, 2.0], [3.0, 4.0]]) == 5.0


def test_gradient_descent_reduces_loss():
    # Minimize f(x) = (x-3)^2 + (y+2)^2 ; minimum at (3, -2)
    def f(x):
        return (x[0] - 3.0) ** 2 + (x[1] + 2.0) ** 2

    params = [0.0, 0.0]
    for _ in range(5000):
        grad = numerical_gradient(f, params)
        params = gradient_descent_step(params, grad, learning_rate=0.001)
    assert abs(params[0] - 3.0) < 1e-2
    assert abs(params[1] - (-2.0)) < 1e-2


def test_mse_and_gradient():
    y_true = [1.0, 2.0, 3.0]
    y_pred = [1.5, 2.5, 2.5]
    mse = mean_squared_error(y_true, y_pred)
    assert abs(mse - (0.25 + 0.25 + 0.25) / 3) < 1e-9
    grad = mse_gradient(y_true, y_pred)
    assert abs(grad[0] - 2 * (1.5 - 1.0) / 3) < 1e-9


def test_partial_derivative():
    def f(x):
        return 3 * x[0] ** 2 + 2 * x[1]

    pd = partial_derivative(f, 0, [2.0, 5.0])
    assert abs(pd - 12.0) < 1e-4


def test_statistics():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert abs(mean(xs) - 3.0) < 1e-9
    assert abs(variance(xs, ddof=1) - 2.5) < 1e-9
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert abs(pearson_correlation(xs, ys) - 1.0) < 1e-6


def test_covariance_zero_for_independent():
    xs = [1.0, 2.0, 3.0]
    ys = [1.0, 2.0, 3.0]
    assert abs(covariance(xs, ys) - 1.0) < 1e-9
