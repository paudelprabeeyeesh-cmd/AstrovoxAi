"""Unit tests for Section 2 algebra + Section 3 functions."""

from math_engine.symbolic.algebra import (
    solve_linear, solve_quadratic, simplify_expression, factor_expression,
    expand_expression, solve_log, arithmetic_progression, geometric_progression,
    permutations, combinations,
)
from math_engine.symbolic.functions import (
    linear_function, quadratic_function, exponential, logarithmic, composite,
    inverse_linear, linear_interpolate,
)


def test_solve_linear():
    r = solve_linear(2, -10)
    assert abs(r.result["x"] - 5.0) < 1e-9


def test_solve_quadratic():
    r = solve_quadratic(1, -3, 2)
    assert sorted(r.result["roots"]) == [1.0, 2.0]


def test_simplify_factor_expand():
    assert simplify_expression("x + x").result["simplified"] == "2*x"
    assert factor_expression("x**2 - 1").result["factored"] == "(x - 1)*(x + 1)"
    assert expand_expression("(x + 1)**2").result["expanded"] == "x**2 + 2*x + 1"


def test_log():
    assert abs(solve_log(2, 8).result - 3.0) < 1e-9


def test_sequences():
    assert arithmetic_progression(1, 2, 5).result["sum"] == 25
    assert geometric_progression(1, 2, 4).result["sum"] == 15


def test_perm_comb():
    assert permutations(5, 2).result == 20
    assert combinations(5, 2).result == 10


def test_linear_quadratic_function():
    assert linear_function(2, 3, 4).result["y"] == 11
    assert quadratic_function(1, -3, 2, 2).result["y"] == 0


def test_exp_log():
    assert abs(exponential(2, 3).result - 8) < 1e-9
    assert abs(logarithmic(2, 8).result - 3) < 1e-9


def test_composite_inverse():
    r = composite(lambda x: x + 1, lambda x: x * 2, 3)
    assert r.result["result"] == 7
    assert abs(inverse_linear(2, 3, 7).result - 2.0) < 1e-9


def test_interpolate():
    r = linear_interpolate(0, 0, 10, 100, 5)
    assert abs(r.result - 50) < 1e-9
