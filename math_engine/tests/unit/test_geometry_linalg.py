"""Unit tests for Section 4 geometry + Section 5 linear algebra."""

from math_engine.symbolic.geometry import (
    pythagorean, distance_point, slope_line, trig, trig_identity,
    radians_convert, cosine_rule, hyperbolic, convex_hull,
)
from math_engine.linear_algebra.matrices import (
    vector_op, dot_norm, mat_mul, transpose, identity, mat_inv, determinant,
    rank, solve_linear_system, eig, svd, mat_norm, pca, low_rank_approx,
)


def test_pythagorean():
    assert abs(pythagorean(3, 4).result["c"] - 5.0) < 1e-9


def test_distance():
    r = distance_point(0, 0, 3, 4)
    assert abs(r.result["distance"] - 5.0) < 1e-9


def test_trig_identity():
    r = trig_identity(0.5)
    assert r.result["holds"] is True


def test_mat_ops():
    r = mat_mul([[1, 2], [3, 4]], [[1, 0], [0, 1]])
    assert r.result["result"] == [[1, 2], [3, 4]]
    r = determinant([[1, 2], [3, 4]])
    assert abs(r.result["determinant"] - (-2.0)) < 1e-9
    r = mat_inv([[1, 2], [3, 4]])
    assert r.ok()


def test_eig_svd():
    assert eig([[1, 0], [0, 2]]).ok()
    assert svd([[1, 0], [0, 2]]).ok()


def test_solve_system():
    r = solve_linear_system([[2, 1], [1, -1]], [3, 0])
    assert r.ok()


def test_pca():
    assert pca([[1, 2], [3, 4], [5, 6]], 1).ok()
