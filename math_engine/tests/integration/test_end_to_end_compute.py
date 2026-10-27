"""End-to-end integration tests for the math engine compute path.

These tests exercise the real execution path:
  service.compute -> Dispatcher.dispatch -> domain implementation -> MathResult

They are NOT mocked and NOT hardcoded. Each test records feature, environment,
expected result, observed result, and pass/fail status.
"""

from __future__ import annotations

import math

import pytest

from math_engine.service import compute

REPORT = []


def _record(feature, env, expected, observed, passed):
    REPORT.append(
        {
            "feature": feature,
            "environment": env,
            "expected": expected,
            "observed": observed,
            "pass": passed,
        }
    )


@pytest.mark.integration
class TestMathEngineEndToEnd:
    """Representative operations from each supported domain."""

    def test_arithmetic_addition(self):
        feature = "arithmetic: decimal_add"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = 12.0
        res = compute("S1.T012", "decimal_add", a=5, b=7)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_arithmetic_gcd(self):
        feature = "arithmetic: gcd"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"gcd": 6, "a": 48, "b": 18}
        res = compute("S1.T009", "gcd", a=48, b=18)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_arithmetic_power(self):
        feature = "arithmetic: power"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = 1024.0
        res = compute("S1.T016", "power", base=2, exp=10)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_arithmetic_factorial(self):
        feature = "arithmetic: factorial"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = 120
        res = compute("S1.T029", "factorial", value=5)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_algebra_linear_equation(self):
        feature = "algebra: solve_linear"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"x": 4.0, "type": "unique"}
        res = compute("S2.T040", "solve_linear", a=2, b=-8)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_algebra_quadratic_equation(self):
        feature = "algebra: solve_quadratic"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"roots": [2.0, 1.0], "type": "two_real", "discriminant": 1.0}
        res = compute("S2.T042", "solve_quadratic", a=1, b=-3, c=2)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_algebra_logarithmic_equation(self):
        feature = "algebra: solve_log"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = 3.0
        res = compute("S2.T052", "solve_log", base=2, value=8)
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_coordinate_geometry_distance(self):
        feature = "coordinate geometry: distance_point (0,0)->(3,4)"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"distance": 5.0, "midpoint": [1.5, 2.0]}
        res = compute("S4.T105", "distance_point", x1=0, y1=0, x2=3, y2=4)
        observed = res.get("result")
        ok = (
            res.get("error") is None
            and math.isclose(observed["distance"], 5.0)
            and observed["midpoint"] == [1.5, 2.0]
        )
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["distance"], 5.0)
        assert observed["midpoint"] == [1.5, 2.0]

    def test_vector_matrix_vector_op(self):
        feature = "vector: vector_op add"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"op": "add", "result": [5.0, 7.0, 9.0], "shape": (3,)}
        res = compute("S5.T128", "vector_op", v1=[1, 2, 3], v2=[4, 5, 6], op="add")
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_vector_matrix_dot_norm(self):
        feature = "vector: dot_norm"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"dot": 32.0}
        res = compute("S5.T129", "dot_norm", v1=[1, 2, 3], v2=[4, 5, 6])
        observed = res.get("result")
        ok = res.get("error") is None and math.isclose(observed["dot"], 32.0)
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["dot"], 32.0)

    def test_vector_matrix_mat_mul(self):
        feature = "matrix: mat_mul"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"result": [[19.0, 22.0], [43.0, 50.0]], "shape": (2, 2)}
        res = compute("S5.T131", "mat_mul", a=[[1, 2], [3, 4]], b=[[5, 6], [7, 8]])
        observed = res.get("result")
        _record(feature, env, expected, observed, observed == expected and res.get("error") is None)
        assert res.get("error") is None
        assert observed == expected

    def test_vector_matrix_determinant(self):
        feature = "matrix: determinant"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"determinant": -2.0, "is_singular": False}
        res = compute("S5.T134", "determinant", a=[[1, 2], [3, 4]])
        observed = res.get("result")
        ok = (
            res.get("error") is None
            and math.isclose(observed["determinant"], -2.0)
            and observed["is_singular"] is False
        )
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["determinant"], -2.0)
        assert observed["is_singular"] is False

    def test_calculus_derivative(self):
        feature = "calculus: derivative of x**2 + 3*x"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"derivative": "2*x + 3"}
        res = compute("S6.T179", "derivative", expr="x**2 + 3*x", var="x")
        observed = res.get("result")
        ok = res.get("error") is None and observed["derivative"] == "2*x + 3"
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert observed["derivative"] == "2*x + 3"

    def test_calculus_gradient(self):
        feature = "calculus: gradient of x**2 + y**2"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"gradient": {"x": "2*x", "y": "2*y"}}
        res = compute("S6.T186", "gradient", expr="x**2 + y**2", vars=["x", "y"])
        observed = res.get("result")
        ok = res.get("error") is None and observed["gradient"] == {"x": "2*x", "y": "2*y"}
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert observed["gradient"] == {"x": "2*x", "y": "2*y"}

    def test_probability_expectation(self):
        feature = "probability: expectation"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"expected_value": 2.1}
        res = compute("S8.T273", "expectation", values=[1, 2, 3], probs=[0.2, 0.5, 0.3])
        observed = res.get("result")
        ok = res.get("error") is None and math.isclose(observed["expected_value"], 2.1)
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["expected_value"], 2.1)

    def test_probability_variance(self):
        feature = "probability: variance"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"variance": 2.0, "std": math.sqrt(2.0)}
        res = compute("S8.T274", "variance", values=[1, 2, 3, 4, 5])
        observed = res.get("result")
        ok = (
            res.get("error") is None
            and math.isclose(observed["variance"], 2.0)
            and math.isclose(observed["std"], math.sqrt(2.0))
        )
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["variance"], 2.0)
        assert math.isclose(observed["std"], math.sqrt(2.0))

    def test_statistics_central_tendency(self):
        feature = "statistics: central_tendency"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"mean": 3.0, "median": 3.0}
        res = compute("S9.T317", "central_tendency", data=[1, 2, 3, 4, 5])
        observed = res.get("result")
        ok = (
            res.get("error") is None
            and math.isclose(observed["mean"], 3.0)
            and math.isclose(observed["median"], 3.0)
        )
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["mean"], 3.0)
        assert math.isclose(observed["median"], 3.0)

    def test_transformer_scaled_dot_product_attention(self):
        feature = "transformer: scaled_dot_product_attention"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = {"scale": 1 / math.sqrt(2)}
        res = compute(
            "S16.T643",
            "scaled_dot_product_attention",
            Q=[[1, 0]],
            K=[[1, 0], [0, 1]],
            V=[[1, 2], [3, 4]],
        )
        observed = res.get("result")
        ok = (
            res.get("error") is None
            and math.isclose(observed["scale"], 1 / math.sqrt(2))
            and "attention_weights" in observed
            and "output" in observed
        )
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert math.isclose(observed["scale"], 1 / math.sqrt(2))
        assert "attention_weights" in observed
        assert "output" in observed

    # --- Error / edge cases ---

    def test_invalid_input_rejected(self):
        feature = "invalid input: gcd with non-integer string"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = "error is not None (blocked), no fabricated result"
        res = compute("S1.T009", "gcd", a="not-a-number", b=18)
        observed = res.get("error")
        ok = res.get("error") is not None and res.get("result") is None
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is not None

    def test_unsupported_topic_returns_error(self):
        feature = "unsupported topic: nonexistent topic id"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = "UnsupportedTopicError surfaced as error, status blocked"
        res = compute("S99.T999", "noop", x=1)
        observed = res.get("error")
        ok = res.get("error") is not None
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is not None

    def test_division_by_zero_blocked(self):
        feature = "error handling: division by zero in expression"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = "DomainError surfaced, no fabricated result"
        res = compute("S1.T022", "evaluate_expression", tokens=["1", "/", "0"])
        observed = res.get("error")
        ok = res.get("error") is not None
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is not None

    def test_large_expression(self):
        feature = "large expression: power with huge exponent"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = "validation error (exponent too large), no hang/crash"
        res = compute("S1.T016", "power", base=2, exp=10**6)
        observed = res.get("error")
        ok = res.get("error") is not None
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is not None

    def test_empty_result_handled(self):
        feature = "empty result: factorial of 0"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = 1
        res = compute("S1.T029", "factorial", value=0)
        observed = res.get("result")
        ok = res.get("error") is None and observed == 1
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert observed == 1

    def test_repeated_submission_deterministic(self):
        feature = "repeated submission: same op twice yields identical result"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = "identical results across repeated calls"
        r1 = compute("S2.T042", "solve_quadratic", a=1, b=-3, c=2)
        r2 = compute("S2.T042", "solve_quadratic", a=1, b=-3, c=2)
        observed = (r1.get("result"), r2.get("result"))
        ok = r1.get("error") is None and r1.get("result") == r2.get("result")
        _record(feature, env, expected, observed, ok)
        assert r1.get("error") is None
        assert r1.get("result") == r2.get("result")

    def test_math_notation_structured_result(self):
        feature = "math notation: structured result includes steps/explanation"
        env = "math_engine.service.compute (real dispatcher, no mocks)"
        expected = "result includes non-empty steps list"
        res = compute("S1.T009", "gcd", a=48, b=18)
        observed = res.get("steps")
        ok = res.get("error") is None and isinstance(observed, list) and len(observed) > 0
        _record(feature, env, expected, observed, ok)
        assert res.get("error") is None
        assert isinstance(observed, list) and len(observed) > 0


def test_report_emitted():
    """Document the full matrix as a test artifact."""
    total = len(REPORT)
    passed = sum(1 for r in REPORT if r["pass"])
    print("\n=== MATH ENGINE END-TO-END MATRIX ===")
    for r in REPORT:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"[{status}] {r['feature']} | env={r['environment']}")
        print(f"      expected: {r['expected']}")
        print(f"      observed: {r['observed']}")
    print(f"\nTOTAL: {total} | PASSED: {passed} | FAILED: {total - passed}")
    assert passed == total, f"{total - passed} test(s) failed"
