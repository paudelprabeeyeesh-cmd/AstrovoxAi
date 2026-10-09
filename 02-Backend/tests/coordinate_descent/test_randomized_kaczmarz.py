import math

from coordinate_descent.randomized_kaczmarz import randomized_kaczmarz


def test_randomized_kaczmarz():
    A = [[1.0, 0.0], [0.0, 1.0]]
    b = [3.0, 4.0]
    x = randomized_kaczmarz(A, b, max_iter=1000, seed=42)
    assert math.isclose(x[0], 3.0, abs_tol=0.1)
    assert math.isclose(x[1], 4.0, abs_tol=0.1)


def test_randomized_kaczmarz_overdetermined():
    A = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    b = [2.0, 3.0, 5.0]
    x = randomized_kaczmarz(A, b, max_iter=2000, seed=42)
    residual = math.sqrt(
        sum(
            (sum(xi * xj for xi, xj in zip(row, x)) - bi) ** 2
            for row, bi in zip(A, b)
        )
    )
    assert residual < 0.1
