from advanced_optimization.trust_region import trust_region_dogleg


def test_trust_region_dogleg_quadratic():
    A = [[2.0, 0.0], [0.0, 3.0]]
    b = [1.0, 2.0]
    grad = lambda x: [A[0][0] * x[0] - b[0], A[1][1] * x[1] - b[1]]
    hess = lambda x: [row[:] for row in A]
    x = trust_region_dogleg(grad, hess, [5.0, 5.0])
    assert abs(x[0] - 0.5) < 1e-3
    assert abs(x[1] - 2.0 / 3.0) < 1e-3


def test_trust_region_dogleg_small_radius():
    A = [[2.0, 0.0], [0.0, 2.0]]
    b = [0.0, 0.0]
    grad = lambda x: [A[0][0] * x[0] - b[0], A[1][1] * x[1] - b[1]]
    hess = lambda x: [row[:] for row in A]
    x = trust_region_dogleg(grad, hess, [1.0, 1.0], radius=0.5)
    assert abs(x[0]) < 1.0
    assert abs(x[1]) < 1.0


def test_trust_region_dogleg_returns_list():
    grad = lambda x: [2 * (x[0] - 1)]
    hess = lambda x: [[2.0]]
    x = trust_region_dogleg(grad, hess, [0.0])
    assert isinstance(x, list)
