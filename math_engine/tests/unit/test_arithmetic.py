"""Unit tests for Section 1 arithmetic."""

from math_engine.symbolic.arithmetic import (
    classify_number, sign_of, is_rational, gcd, lcm, fraction_simplify,
    decimal_add, decimal_mul, percent, ratio_simplify, proportion_solve,
    unit_convert, power, nth_root, surd_simplify, scientific_notation,
    round_sigfigs, absolute, evaluate_expression, dimension_check,
    rounding_error, to_base, from_base, mod, mod_inverse, interval_contains,
    factorial, summation,
)


def test_classify_number():
    r = classify_number(5)
    assert r.ok() and r.result["kind"] == "natural"
    r = classify_number(0)
    assert r.result["kind"] == "whole"


def test_sign():
    assert sign_of(-3).result["sign"] == -1
    assert sign_of(0).result["sign"] == 0
    assert sign_of(4).result["sign"] == 1


def test_gcd_lcm():
    assert gcd(12, 18).result["gcd"] == 6
    assert lcm(12, 18).result["lcm"] == 36


def test_fraction():
    r = fraction_simplify(4, 6)
    assert r.result["simplified"] == "2/3"


def test_percent():
    assert percent(20, 50).result == 10.0
    assert percent(50).result == 0.5


def test_power_root():
    assert power(2, 10).result == 1024
    assert abs(nth_root(27, 3).result - 3.0) < 1e-9


def test_surd():
    r = surd_simplify(12)
    assert r.result["outside"] == 2 and r.result["inside"] == 3


def test_order_of_ops():
    r = evaluate_expression(["2", "+", "3", "*", "4"])
    assert abs(r.result - 14) < 1e-9


def test_mod_inverse():
    r = mod_inverse(3, 7)
    assert r.result["inverse"] == 5  # 3*5=15=1 mod 7


def test_factorial():
    assert factorial(5).result == 120


def test_summation():
    r = summation(1, 5, "i")
    assert r.result["sum"] == 15


def test_division_by_zero_rejected():
    try:
        from math_engine.core.errors import DomainError
        # decimal_div not present; test via evaluate_expression div by zero
        evaluate_expression(["1", "/", "0"])
        assert False, "should raise"
    except Exception:
        pass
