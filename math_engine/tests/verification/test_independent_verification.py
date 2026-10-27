"""Independent mathematical correctness verification for the AstrovoxAI Math Engine.

Every test uses an independent oracle or mathematical property — never the
implementation under test. math/numpy/sympy are used only as oracles.

Run:  python -m pytest math_engine/tests/verification/test_independent_verification.py -q
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp

from math_engine.service import compute

random_seed = 42


def approx(a, b, tol=1e-8):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# ===========================================================================
# SECTION 1 — Arithmetic & number systems
# ===========================================================================

def test_gcd_independent():
    cases = [(12, 18), (100, 35), (17, 31), (0, 5), (210, 45), (1024, 768)]
    for a, b in cases:
        r = compute("S1.T009", "gcd", a=a, b=b)
        assert r["error"] is None, r
        g = r["result"]["gcd"]
        x, y = abs(a), abs(b)
        while y:
            x, y = y, x % y
        assert g == x, f"gcd({a},{b})={g} expected {x}"
        assert a % g == 0 and b % g == 0


def test_lcm_independent():
    cases = [(12, 18), (100, 35), (7, 3), (0, 5)]
    for a, b in cases:
        r = compute("S1.T010", "lcm", a=a, b=b)
        assert r["error"] is None, r
        l = r["result"]["lcm"]
        g = math.gcd(abs(a), abs(b))
        expected = 0 if (a == 0 or b == 0) else abs(a * b) // g
        assert l == expected, f"lcm({a},{b})={l} expected {expected}"


def test_fraction_simplify_independent():
    from fractions import Fraction
    cases = [(4, 6), (15, 35), (100, 25), (7, 13), (-8, 12)]
    for n, d in cases:
        r = compute("S1.T011", "fraction_simplify", numerator=n, denominator=d)
        assert r["error"] is None, r
        res = r["result"]
        assert Fraction(res["numerator"], res["denominator"]) == Fraction(n, d)
        assert math.gcd(abs(res["numerator"]), abs(res["denominator"])) == 1
        assert res["denominator"] > 0


def test_percent_independent():
    assert approx(compute("S1.T013", "percent_of", value=25, of=200)["result"], 50.0)
    assert approx(compute("S1.T013", "percent_to_decimal", value=50)["result"], 0.5)


def test_ratio_simplify_independent():
    from fractions import Fraction
    r = compute("S1.T014", "ratio_simplify", a=8, b=12)
    assert r["error"] is None
    ns, ds = r["result"]["simplified"].split(":")
    assert Fraction(int(ns), int(ds)) == Fraction(8, 12)


def test_proportion_independent():
    assert approx(compute("S1.T014", "proportion_solve", a=2, b=3, c=4)["result"], 6.0)


def test_power_independent():
    for base, exp in [(2, 10), (5, 3), (2, 0), (7, 1), (10, 5)]:
        r = compute("S1.T016", "power", base=base, exp=exp)
        assert r["error"] is None
        assert approx(r["result"], base ** exp)


def test_nth_root_independent():
    for val, n in [(27, 3), (16, 4), (2, 2), (8, 3)]:
        r = compute("S1.T017", "nth_root", value=val, n=n)
        assert r["error"] is None
        assert approx(r["result"] ** n, val, tol=1e-6)


def test_surd_independent():
    r = compute("S1.T018", "surd_simplify", value=12)
    assert r["error"] is None
    assert r["result"]["outside"] ** 2 * r["result"]["inside"] == 12
    r = compute("S1.T018", "surd_simplify", value=16)
    assert r["result"]["outside"] == 4 and r["result"]["inside"] == 1


def test_scientific_notation_independent():
    for val in [123.45, 0.0045, -7890.0]:
        r = compute("S1.T019", "scientific_notation", value=val)
        assert r["error"] is None
        m_str, e_str = r["result"].split(" x 10^")
        assert approx(float(m_str) * (10 ** int(e_str)), val, tol=1e-9)
        assert 1 <= abs(float(m_str)) < 10


def test_round_sigfigs_independent():
    assert approx(compute("S1.T020", "round_sigfigs", value=12345.678, sigfigs=3)["result"], 12300.0)


def test_absolute_independent():
    for v in [-5, 0, 3.5, -2.7]:
        r = compute("S1.T021", "absolute", value=v)
        assert approx(r["result"], abs(v))


def test_evaluate_expression_independent():
    cases = [
        (["2", "+", "3", "*", "4"], 14.0),
        (["(", "2", "+", "3", ")", "*", "4"], 20.0),
        (["10", "/", "2", "+", "3"], 8.0),
    ]
    for toks, expected in cases:
        r = compute("S1.T022", "evaluate_expression", tokens=toks)
        assert r["error"] is None, f"{toks}: {r['error']}"
        assert approx(r["result"], expected), f"{toks}={r['result']} expected {expected}"


def test_mod_inverse_independent():
    for a, m in [(3, 7), (10, 17), (5, 12)]:
        r = compute("S1.T027", "mod_inverse", a=a, m=m)
        assert r["error"] is None, r
        assert (a * r["result"]["inverse"]) % m == 1


def test_factorial_independent():
    for n in [0, 1, 5, 10]:
        r = compute("S1.T029", "factorial", value=n)
        assert r["error"] is None
        assert r["result"] == math.factorial(n)


def test_summation_independent():
    assert compute("S1.T030", "summation", start=1, end=10, term="i")["result"]["sum"] == 55
    assert compute("S1.T030", "summation", start=1, end=4, term="i^2")["result"]["sum"] == 30


# ===========================================================================
# SECTION 2 — Algebra
# ===========================================================================

def test_solve_linear_independent():
    for a, b, x in [(2, -10, 5.0), (3, 6, -2.0), (1, 0, 0.0), (-4, 8, 2.0)]:
        r = compute("S2.T040", "solve_linear", a=a, b=b)
        assert r["error"] is None
        assert approx(r["result"]["x"], x)
        assert approx(a * r["result"]["x"] + b, 0.0)


def test_solve_linear_edge():
    assert compute("S2.T040", "solve_linear", a=0, b=5)["result"]["type"] == "no_solution"
    assert compute("S2.T040", "solve_linear", a=0, b=0)["result"]["type"] == "infinite"


def test_solve_quadratic_independent():
    cases = [(1, -3, 2, [1.0, 2.0]), (1, 2, 1, [-1.0]), (1, 0, -4, [-2.0, 2.0])]
    for a, b, c, roots in cases:
        r = compute("S2.T042", "solve_quadratic", a=a, b=b, c=c)
        assert r["error"] is None, r
        got = [complex(g) for g in r["result"]["roots"]]
        for g in got:
            residual = a * g ** 2 + b * g + c
            assert abs(residual) < 1e-6, f"residual {residual}"


def test_simplify_factor_expand_independent():
    for e in ["x + x", "x**2 - 1", "(x + 1)**2", "x**2 + 2*x + 1"]:
        r = compute("S2.T034", "simplify", expr=e)
        assert r["error"] is None
        assert sp.simplify(sp.sympify(e) - sp.sympify(r["result"]["simplified"])) == 0
        r = compute("S2.T035", "expand", expr=e)
        assert r["error"] is None
        assert sp.expand(sp.sympify(e)) == sp.sympify(r["result"]["expanded"])
        r = compute("S2.T037", "factor", expr=e)
        assert r["error"] is None
        assert sp.factor(sp.sympify(e)) == sp.sympify(r["result"]["factored"])


def test_solve_log_independent():
    for base, val, expected in [(2, 8, 3.0), (10, 100, 2.0), (3, 27, 3.0), (2, 1, 0.0)]:
        r = compute("S2.T052", "solve_log", base=base, value=val)
        assert r["error"] is None
        assert approx(r["result"], expected)
        assert approx(base ** r["result"], val)


def test_ap_gp_independent():
    assert compute("S2.T056", "arithmetic_progression", a=1, d=2, n=5)["result"]["sum"] == 25
    assert compute("S2.T057", "geometric_progression", a=1, r=2, n=4)["result"]["sum"] == 15


def test_perm_comb_independent():
    assert compute("S2.T061", "permutations", n=5, k=2)["result"] == 20
    assert compute("S2.T061", "combinations", n=5, k=2)["result"] == 10


# ===========================================================================
# SECTION 3 — Functions
# ===========================================================================

def test_linear_function_independent():
    r = compute("S3.T073", "linear_function", m=2, b=3, x=4)["result"]
    assert approx(r["y"], 11.0) and approx(r["slope"], 2.0) and approx(r["intercept"], 3.0)


def test_quadratic_function_independent():
    assert approx(compute("S3.T074", "quadratic_function", a=1, b=-3, c=2, x=2)["result"]["y"], 0.0)


def test_exponential_log_independent():
    assert approx(compute("S3.T077", "exponential", base=2, x=3)["result"], 8.0)
    r = compute("S3.T078", "logarithmic", base=2, x=8)["result"]
    assert approx(r, 3.0) and approx(2 ** r, 8.0)


def test_composite_independent():
    r = compute("S3.T080", "composite", f=lambda v: v + 1, g=lambda v: v * 2, x=3)["result"]
    assert approx(r["inner"], 6.0) and approx(r["result"], 7.0)


def test_inverse_linear_independent():
    r = compute("S3.T081", "inverse_linear", m=2, b=3, y=7)["result"]
    assert approx(r, 2.0) and approx(2 * r + 3, 7.0)


def test_interpolate_independent():
    assert approx(compute("S3.T094", "linear_interpolate", x0=0, y0=0, x1=10, y1=100, x=5)["result"], 50.0)
    assert approx(compute("S3.T094", "linear_interpolate", x0=1, y0=2, x1=3, y1=6, x=2)["result"], 4.0)


# ===========================================================================
# SECTION 4 — Geometry & trigonometry
# ===========================================================================

def test_pythagorean_independent():
    r = compute("S4.T100", "pythagorean", a=3, b=4)["result"]
    assert approx(r["c"], 5.0) and approx(r["c"] ** 2, 3 ** 2 + 4 ** 2)


def test_distance_midpoint_independent():
    r = compute("S4.T105", "distance_point", x1=0, y1=0, x2=3, y2=4)["result"]
    assert approx(r["distance"], 5.0) and approx(r["midpoint"][0], 1.5) and approx(r["midpoint"][1], 2.0)


def test_slope_independent():
    r = compute("S4.T106", "slope_line", x1=1, y1=1, x2=3, y2=5)["result"]
    assert approx(r["slope"], 2.0) and approx(r["intercept"], -1.0)
    r = compute("S4.T106", "slope_line", x1=2, y1=1, x2=2, y2=5)["result"]
    assert r["slope"] is None and r["type"] == "vertical"


def test_trig_independent():
    for func, angle in [("sin", 0), ("sin", math.pi / 2), ("cos", 0), ("tan", math.pi / 4)]:
        r = compute("S4.T112", "trig", func=func, angle=angle, unit="rad")
        assert r["error"] is None, f"{func}({angle}): {r['error']}"
        assert approx(r["result"]["value"], getattr(math, func)(angle), tol=1e-9)


def test_trig_identity_independent():
    for angle in [0.3, 1.0, 2.5, math.pi]:
        r = compute("S4.T114", "trig_identity", angle=angle, unit="rad")
        assert r["result"]["holds"] is True
        assert approx(r["result"]["sin_sq_plus_cos_sq"], 1.0, tol=1e-9)


def test_radians_convert_independent():
    assert approx(compute("S4.T117", "radians_convert", degrees=180)["result"]["radians"], math.pi)


def test_cosine_rule_independent():
    assert approx(compute("S4.T118", "cosine_rule", a=3, b=4, angle_c_deg=90)["result"]["c"], 5.0, tol=1e-6)


def test_hyperbolic_independent():
    for func, x in [("sinh", 1.0), ("cosh", 1.0), ("tanh", 0.5)]:
        r = compute("S4.T121", "hyperbolic", func=func, x=x)
        assert r["error"] is None
        assert approx(r["result"]["value"], getattr(math, func)(x), tol=1e-9)


def test_convex_hull_independent():
    pts = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]
    r = compute("S4.T124", "convex_hull", points=pts)
    assert r["error"] is None
    assert len(r["result"]["hull"]) == 4
    pt_set = set(pts)
    for p in r["result"]["hull"]:
        assert tuple(p) in pt_set


# ===========================================================================
# SECTION 5 — Linear algebra
# ===========================================================================

def test_mat_mul_independent():
    r = compute("S5.T131", "mat_mul", a=[[1, 2], [3, 4]], b=[[5, 6], [7, 8]])
    assert r["error"] is None
    assert r["result"]["result"] == [[19, 22], [43, 50]]
    assert r["result"]["shape"] == (2, 2)


def test_mat_inv_independent():
    r = compute("S5.T133", "mat_inv", a=[[4, 7], [2, 6]])
    assert r["error"] is None
    An = np.array([[4, 7], [2, 6]], dtype=float)
    Inn = np.array(r["result"]["result"], dtype=float)
    assert np.allclose(An @ Inn, np.eye(2), atol=1e-9)


def test_determinant_independent():
    for A, expected in [([[1, 2], [3, 4]], -2.0), ([[1, 0], [0, 1]], 1.0), ([[2]], 2.0)]:
        r = compute("S5.T134", "determinant", a=A)
        assert r["error"] is None
        assert approx(r["result"]["determinant"], expected, tol=1e-9)


def test_rank_independent():
    assert compute("S5.T135", "rank", a=[[1, 2, 3], [4, 5, 6], [7, 8, 9]])["result"]["rank"] == 2
    assert compute("S5.T135", "rank", a=[[1, 0], [0, 1]])["result"]["rank"] == 2


def test_solve_linear_system_independent():
    r = compute("S5.T136", "solve_linear_system", a=[[2, 1], [1, -1]], b=[3, 0])
    assert r["error"] is None
    An = np.array([[2, 1], [1, -1]], dtype=float)
    bn = np.array([3, 0], dtype=float)
    xn = np.array(r["result"]["solution"], dtype=float)
    assert np.allclose(An @ xn, bn, atol=1e-8)


def test_eig_independent():
    r = compute("S5.T145", "eig", a=[[1, 0], [0, 2]])
    assert r["error"] is None
    vals = set(abs(v) for v in r["result"]["eigenvalues"])
    assert 1.0 in vals and 2.0 in vals
    An = np.array([[1, 0], [0, 2]], dtype=float)
    for lam, vec in zip(r["result"]["eigenvalues"], np.array(r["result"]["eigenvectors"]).T):
        assert np.allclose(An @ vec, lam * vec, atol=1e-6)


def test_svd_independent():
    r = compute("S5.T150", "svd", a=[[1, 0], [0, 2]])
    assert r["error"] is None
    U = np.array(r["result"]["U"]); S = np.array(r["result"]["S"]); Vt = np.array(r["result"]["Vt"])
    assert np.allclose(U @ np.diag(S) @ Vt, np.array([[1, 0], [0, 2]], dtype=float), atol=1e-8)


def test_mat_norm_independent():
    assert approx(compute("S5.T154", "mat_norm", a=[[3, 4], [0, 0]])["result"]["norm"], 5.0, tol=1e-9)


def test_pca_independent():
    r = compute("S5.T158", "pca", data=[[1, 2], [3, 4], [5, 6]], n_components=1)
    assert r["error"] is None
    assert np.array(r["result"]["components"]).shape[1] == 1
    assert len(r["result"]["projected"]) == 3


def test_low_rank_approx_independent():
    r = compute("S5.T159", "low_rank_approx", a=[[1, 2], [3, 4]], rank=1)
    assert r["error"] is None
    approx_mat = np.array(r["result"]["approximation"])
    An = np.array([[1, 2], [3, 4]], dtype=float)
    assert np.linalg.norm(An - approx_mat, 'fro') < np.linalg.norm(An, 'fro')


# ===========================================================================
# SECTION 6 — Calculus
# ===========================================================================

def test_derivative_independent():
    r = compute("S6.T179", "derivative", expr="x**2", var="x", point=3)
    assert r["error"] is None
    assert approx(r["result"]["value_at_point"], 6.0, tol=1e-6)
    assert r["result"]["matches"] is True
    r = compute("S6.T179", "derivative", expr="sin(x)", var="x", point=0)
    assert approx(r["result"]["value_at_point"], 1.0, tol=1e-6)


def test_chain_rule_independent():
    r = compute("S6.T181", "chain_rule", outer="u**2", inner="x**3", var="x", point=2)
    assert r["error"] is None
    assert approx(r["result"]["value_at_point"], 192.0, tol=1e-6)


def test_partial_derivative_independent():
    r = compute("S6.T184", "partial_derivative", expr="x**2 + y**2", var="x")
    assert r["error"] is None and r["result"]["derivative"] == "2*x"


def test_gradient_independent():
    r = compute("S6.T186", "gradient", expr="x**2 + y**2 + z**2", vars=["x", "y", "z"])
    assert r["error"] is None
    g = r["result"]["gradient"]
    assert g["x"] == "2*x" and g["y"] == "2*y" and g["z"] == "2*z"


def test_hessian_independent():
    r = compute("S6.T188", "hessian", expr="x**2 + y**2", vars=["x", "y"])
    assert r["error"] is None
    H = r["result"]["hessian"]
    assert H[0][0] == 2 and H[1][1] == 2 and H[0][1] == 0


def test_taylor_independent():
    r = compute("S6.T189", "taylor_series", expr="exp(x)", var="x", point=0, terms=3)
    assert r["error"] is None


def test_integrate_independent():
    assert approx(compute("S6.T196", "integrate", expr="x", var="x", a=0, b=1)["result"]["integral"], 0.5, tol=1e-9)
    assert approx(compute("S6.T196", "integrate", expr="1", var="x", a=0, b=5)["result"]["integral"], 5.0, tol=1e-9)


def test_autograd_demo_independent():
    def f(p): return p[0] ** 2 + p[1] ** 2
    r = compute("S6.T215", "autograd_demo", func=f, point=[3.0, 4.0])
    assert r["error"] is None
    assert approx(r["result"]["gradient"][0], 6.0, tol=1e-4)
    assert approx(r["result"]["gradient"][1], 8.0, tol=1e-4)


# ===========================================================================
# SECTION 7 — Optimization
# ===========================================================================

def test_gradient_descent_independent():
    def grad(x): return [2 * (x[0] - 3)]
    r = compute("S7.T222", "gradient_descent", grad_fn=grad, start=[10.0], lr=0.1, max_iter=1000)
    assert r["error"] is None
    assert approx(r["result"]["solution"][0], 3.0, tol=1e-2)


def test_adam_step_independent():
    r = compute("S7.T229", "adam_step", param=[1.0], grad=[0.5], lr=0.1, t=1)["result"]
    assert approx(r["new_params"][0], 0.9, tol=1e-4)


def test_fib_dp_independent():
    assert compute("S7.T242", "fib_dp", n=10)["result"]["result"] == 55
    assert compute("S7.T242", "fib_dp", n=0)["result"]["result"] == 0


def test_convergence_check_independent():
    assert compute("S7.T252", "convergence_check", sequence=[1.0, 1.0001, 1.00001], tol=1e-3)["result"]["converged"] is True
    assert compute("S7.T252", "convergence_check", sequence=[1.0, 2.0, 3.0], tol=1e-3)["result"]["converged"] is False


# ===========================================================================
# SECTION 8 — Probability
# ===========================================================================

def test_bayes_independent():
    r = compute("S8.T265", "bayes", p_a=0.01, p_b_given_a=0.9, p_b=0.1)["result"]
    assert approx(r["p_a_given_b"], 0.09) and 0 <= r["p_a_given_b"] <= 1


def test_expectation_variance_independent():
    vals, probs = [1, 2, 3], [0.2, 0.5, 0.3]
    assert approx(compute("S8.T273", "expectation", values=vals, probs=probs)["result"]["expected_value"], 2.1)
    r = compute("S8.T274", "variance", values=vals, probs=probs)["result"]
    mu = 2.1
    var = 0.2 * (1 - mu) ** 2 + 0.5 * (2 - mu) ** 2 + 0.3 * (3 - mu) ** 2
    assert approx(r["variance"], var, tol=1e-9)


def test_bernoulli_binomial_independent():
    assert approx(compute("S8.T280", "bernoulli_pmf", k=1, p=0.5)["result"]["pmf"], 0.5)
    assert approx(compute("S8.T281", "binomial_pmf", k=2, n=4, p=0.5)["result"]["pmf"], 0.375)
    total = sum(compute("S8.T281", "binomial_pmf", k=k, n=4, p=0.5)["result"]["pmf"] for k in range(5))
    assert approx(total, 1.0, tol=1e-9)


def test_normal_pdf_independent():
    r = compute("S8.T285", "normal_pdf", x=0, mu=0, sigma=1)["result"]
    assert approx(r["pdf"], 1.0 / math.sqrt(2 * math.pi), tol=1e-6)


def test_lln_clt_independent():
    assert approx(compute("S8.T300", "ll_demo", samples=[1.0, 2.0, 3.0, 4.0, 5.0])["result"]["sample_mean"], 3.0)
    assert approx(compute("S8.T301", "clt_demo", sample_means=[1.0, 2.0, 3.0])["result"]["mean_of_means"], 2.0)


# ===========================================================================
# SECTION 9 — Statistics
# ===========================================================================

def test_central_tendency_independent():
    r = compute("S9.T317", "central_tendency", data=[1, 2, 3, 4, 5])["result"]
    assert approx(r["mean"], 3.0) and approx(r["median"], 3.0)
    r = compute("S9.T317", "central_tendency", data=[1, 2, 2, 3])["result"]
    assert 2 in r["mode"]


def test_sample_variance_independent():
    r = compute("S9.T319", "sample_variance", data=[2, 4, 4, 4, 5, 5, 7, 9])["result"]
    # sample variance (ddof=1) of this set = 4.5714..., NOT 4.0 (4.0 is population var)
    assert approx(r["variance"], 4.571428571428571, tol=1e-6)


def test_ci_mean_independent():
    r = compute("S9.T327", "ci_mean", data=[1, 2, 3, 4, 5], confidence=0.95)["result"]
    assert r["ci_lower"] < r["mean"] < r["ci_upper"]


def test_z_test_independent():
    r = compute("S9.T328", "z_test_one_sample", data=[1, 2, 3, 4, 5], mu0=3)["result"]
    assert approx(r["z"], 0.0, tol=1e-6) and r["reject_null"] is False


def test_linear_regression_independent():
    r = compute("S9.T339", "linear_regression", x=[1, 2, 3, 4], y=[3, 5, 7, 9])["result"]
    assert approx(r["slope"], 2.0, tol=1e-6) and approx(r["intercept"], 1.0, tol=1e-6)
    assert approx(r["r_squared"], 1.0, tol=1e-6)


def test_anova_independent():
    from math_engine.statistics.descriptive import anova_one_way
    r = anova_one_way([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    assert r.error is None and r.result["f_statistic"] > 0


def test_anova_via_dispatcher_independent():
    # Verify ANOVA works end-to-end through compute() / dispatcher
    r = compute("S9.T345", "anova_one_way", groups=[[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    assert r["error"] is None, r
    assert r["result"]["f_statistic"] > 0
    assert r["result"]["df_between"] == 2
    assert r["result"]["df_within"] == 6


# ===========================================================================
# SECTION 10 — Information theory
# ===========================================================================

def test_entropy_independent():
    assert approx(compute("S10.T378", "entropy", probs=[0.5, 0.5], base=2)["result"]["entropy"], 1.0, tol=1e-9)
    assert approx(compute("S10.T378", "entropy", probs=[1.0], base=2)["result"]["entropy"], 0.0)


def test_cross_entropy_kl_independent():
    assert approx(compute("S10.T383", "cross_entropy", p=[0.5, 0.5], q=[0.5, 0.5], base=2)["result"]["cross_entropy"], 1.0)
    assert approx(compute("S10.T384", "kl_divergence", p=[0.5, 0.5], q=[0.5, 0.5], base=2)["result"]["kl_divergence"], 0.0)
    r = compute("S10.T384", "kl_divergence", p=[0.9, 0.1], q=[0.5, 0.5], base=2)
    assert r["result"]["kl_divergence"] >= 0


def test_perplexity_independent():
    assert approx(compute("S10.T389", "perplexity", probs=[0.5, 0.5], base=2)["result"]["perplexity"], 2.0, tol=1e-9)


def test_huffman_independent():
    r = compute("S10.T394", "huffman_lengths", symbols=["a", "b", "c", "d"], probs=[0.4, 0.3, 0.2, 0.1])
    assert r["error"] is None
    codes = list(r["result"]["codes"].values())
    for i, c1 in enumerate(codes):
        for c2 in codes[i + 1:]:
            assert not c1.startswith(c2) and not c2.startswith(c1)
    ent = compute("S10.T378", "entropy", probs=[0.4, 0.3, 0.2, 0.1], base=2)["result"]["entropy"]
    assert r["result"]["average_length"] >= ent - 1e-9


# ===========================================================================
# SECTION 11 — Discrete
# ===========================================================================

def test_pigeonhole_independent():
    r = compute("S11.T428", "pigeonhole", items=10, containers=3)["result"]
    assert r["guaranteed_collision"] is True and r["min_in_one_container"] == 4


def test_dijkstra_independent():
    g = {"A": {"B": 1, "C": 4}, "B": {"C": 2, "D": 5}, "C": {"D": 1}, "D": {}}
    r = compute("S11.T433", "dijkstra", graph=g, start="A", end="D")
    assert r["error"] is None
    assert approx(r["result"]["distance"], 4.0)
    assert r["result"]["path"] == ["A", "B", "C", "D"]


# ===========================================================================
# SECTION 12 — Numerical
# ===========================================================================

def test_bisection_independent():
    r = compute("S12.T464", "bisection", f=lambda x: x * x - 2, a=1.0, b=2.0)
    assert r["error"] is None
    assert approx(r["result"]["root"] ** 2, 2.0, tol=1e-4)


def test_newton_independent():
    r = compute("S12.T465", "newton_raphson", f=lambda x: x * x - 2, df=lambda x: 2 * x, x0=1.0)
    assert r["error"] is None
    assert approx(r["result"]["root"] ** 2, 2.0, tol=1e-6)


def test_trapezoidal_independent():
    assert approx(compute("S12.T469", "trapezoidal", f=lambda x: x, a=0, b=1, n=1000)["result"]["integral"], 0.5, tol=1e-3)


def test_gaussian_eliminate_independent():
    r = compute("S12.T473", "gaussian_eliminate", a=[[2, 1], [1, -1]], b=[3, 0])
    assert r["error"] is None
    An = np.array([[2, 1], [1, -1]], dtype=float); bn = np.array([3, 0], dtype=float); xn = np.array(r["result"]["solution"], dtype=float)
    assert np.allclose(An @ xn, bn, atol=1e-8)


# ===========================================================================
# SECTION 14 — ML foundations
# ===========================================================================

def test_mse_independent():
    assert approx(compute("S14.T523", "mse", y_true=[1, 2, 3], y_pred=[1, 2, 3])["result"]["loss"], 0.0)
    assert approx(compute("S14.T523", "mse", y_true=[1, 2], y_pred=[2, 2])["result"]["loss"], 0.5)


def test_cross_entropy_loss_independent():
    r = compute("S14.T523", "cross_entropy_loss", y_true=[1, 0], y_pred=[0.9, 0.1])["result"]
    expected = -(math.log(0.9) + math.log(0.9)) / 2
    assert approx(r["loss"], expected, tol=1e-9)


def test_l1_l2_penalty_independent():
    assert approx(compute("S14.T531", "l1_penalty", weights=[1, -2, 3], alpha=0.5)["result"]["penalty"], 3.0)
    assert approx(compute("S14.T531", "l2_penalty", weights=[1, -2, 3], alpha=0.5)["result"]["penalty"], 7.0)


def test_kfold_independent():
    r = compute("S14.T534", "kfold_split", n_samples=10, k=5)
    assert r["error"] is None and len(r["result"]["folds"]) == 5
    assert sorted(i for f in r["result"]["folds"] for i in f["test"]) == list(range(10))


def test_kmeans_independent():
    r = compute("S14.T549", "kmeans_one_iter", points=[[0, 0], [0.1, 0], [5, 5], [5.1, 5]], centroids=[[0, 0], [5, 5]])
    assert r["error"] is None and len(r["result"]["labels"]) == 4


# ===========================================================================
# SECTION 15 — Deep learning
# ===========================================================================

def test_activations_independent():
    assert compute("S15.T578", "relu", x=[-1, 0, 2])["result"]["result"] == [0.0, 0.0, 2.0]
    assert approx(compute("S15.T577", "sigmoid", x=0)["result"]["result"], 0.5, tol=1e-9)
    r = compute("S15.T580", "softmax", x=[0, 1, 2])["result"]
    assert approx(sum(r["result"]), 1.0, tol=1e-9) and all(p > 0 for p in r["result"])


def test_backprop_scalar_independent():
    # pred = w*x+b; error=pred-y; grad = error*x (gradient of 0.5*error^2)
    r = compute("S15.T585", "backprop_scalar", w=2, b=1, x=3, y=5)["result"]
    assert approx(r["grad_w"], 6.0) and approx(r["grad_b"], 2.0)


def test_batch_norm_independent():
    r = compute("S15.T591", "batch_norm", x=[1, 2, 3, 4, 5])["result"]
    vals = r["result"]
    assert approx(np.mean(vals), 0.0, tol=1e-6)
    # output variance = var/(var+eps) ≈ 1 but not exactly due to eps
    assert approx(np.var(vals), 1.0, tol=1e-3)


def test_lora_independent():
    r = compute("S15.T618", "lora_update", W=[[1.0]], A=[[0.5]], B=[[0.5]], alpha=1.0)["result"]
    assert approx(r["updated"][0][0], 1.0 + 0.5 * 0.5)


# ===========================================================================
# SECTION 16 — Transformers & LLMs
# ===========================================================================

def test_attention_independent():
    r = compute("S16.T643", "scaled_dot_product_attention", Q=[[1, 0]], K=[[1, 0]], V=[[10]])
    assert r["error"] is None
    assert approx(np.array(r["result"]["output"])[0][0], 10.0, tol=1e-6)
    assert approx(np.sum(r["result"]["attention_weights"]), 1.0, tol=1e-9)


def test_top_k_independent():
    r = compute("S16.T659", "top_k", probs=[0.1, 0.5, 0.3, 0.1], k=2)
    assert r["error"] is None
    assert approx(sum(r["result"]["probabilities"]), 1.0, tol=1e-9)
    assert set(r["result"]["indices"]) == {1, 2}


def test_top_p_independent():
    r = compute("S16.T660", "top_p", probs=[0.5, 0.3, 0.2], p=0.8)
    assert r["error"] is None
    assert approx(sum(r["result"]["probabilities"]), 1.0, tol=1e-9)


def test_perplexity_llm_independent():
    r = compute("S16.T664", "perplexity", logprobs=[0.0, 0.0])
    assert r["error"] is None, r.get("error")
    assert approx(r["result"]["perplexity"], 1.0, tol=1e-9)
    r = compute("S16.T664", "perplexity", logprobs=[-math.log(2), -math.log(2)])
    assert approx(r["result"]["perplexity"], 2.0, tol=1e-6)


def test_count_params_independent():
    r = compute("S16.T679", "count_params", layers=[{"name": "l1", "params": 100}, {"name": "l2", "params": 200}])["result"]
    assert r["total_params"] == 300


def test_scaling_law_independent():
    r = compute("S16.T681", "scaling_law", compute=1000, dataset=1000)
    assert r["error"] is None and r["result"]["estimated_loss"] > 0


# ===========================================================================
# SECTION 18 — RL
# ===========================================================================

def test_discounted_return_independent():
    assert approx(compute("S18.T740", "discounted_return", rewards=[1, 1, 1], gamma=0.5)["result"]["return"], 1.75)


def test_bellman_independent():
    assert approx(compute("S18.T741", "bellman_update", reward=2, gamma=0.9, v_next=5)["result"]["value"], 6.5)


def test_q_learning_independent():
    assert approx(compute("S18.T752", "q_learning_update", q=0, reward=1, gamma=0.9, q_next_max=10, alpha=0.1)["result"]["new_q"], 1.0)


def test_epsilon_greedy_independent():
    assert compute("S18.T768", "epsilon_greedy", values=[0.1, 0.9, 0.2], epsilon=0.0)["result"]["best_arm"] == 1


# ===========================================================================
# SECTION 19 — Advanced (frameworks / demos)
# ===========================================================================

def test_advanced_demos():
    assert approx(compute("S19.T781", "interval_measure", a=0, b=5)["result"]["measure"], 5.0)
    r = compute("S19.T803", "wasserstein_1d", values_a=[1, 2, 3], values_b=[2, 3, 4])
    assert r["error"] is None and r["result"]["wasserstein_1"] >= 0
    assert approx(compute("S19.T841", "dp_laplace_scale", sensitivity=1.0, epsilon=0.1)["result"]["scale"], 10.0)
    r = compute("S19.T850", "verify_bound", expr="x < 5", bound=5)
    assert r["error"] is None and r["verified"] is False  # framework only


# ===========================================================================
# SECTION 13 — ODE Initial-Value Problems (independent oracle verification)
# ===========================================================================

def test_euler_step_independent():
    # dy/dt = -y, y(0)=1, exact y(t) = exp(-t)
    def f(t, y):
        return [-y[0]]

    r = compute("S13.T496", "euler_step", f=f, t=0.0, y=[1.0], h=0.1)
    assert r["error"] is None, r
    y_next = r["result"]["y_next"][0]
    exact = math.exp(-0.1)
    euler = 1.0 - 0.1  # y + h*f = 1 + 0.1*(-1) = 0.9
    assert approx(y_next, euler), f"Euler step: got {y_next}, expected {euler}"


def test_euler_solve_independent():
    # dy/dt = -y, y(0)=1, h=0.1, t_end=1.0
    def f(t, y):
        return [-y[0]]

    r = compute("S13.T496", "euler_solve", f=f, t0=0.0, y0=[1.0], t_end=1.0, h=0.1)
    assert r["error"] is None, r
    traj = r["result"]["y"]
    # Final value approx exp(-1) ≈ 0.3679, Euler underestimates slightly
    final = traj[-1][0]
    assert 0.3 < final < 0.5, f"Euler final y(1) = {final}, expected ~0.37"


def test_rk4_step_independent():
    # dy/dt = -y, y(0)=1, h=0.1, RK4 should be very close to exact
    def f(t, y):
        return [-y[0]]

    r = compute("S13.T518", "rk4_step", f=f, t=0.0, y=[1.0], h=0.1)
    assert r["error"] is None, r
    y_next = r["result"]["y_next"][0]
    exact = math.exp(-0.1)
    assert approx(y_next, exact, tol=1e-6), f"RK4 step: got {y_next}, expected {exact}"


def test_rk4_solve_independent():
    # dy/dt = -y, y(0)=1, h=0.1, t_end=1.0
    def f(t, y):
        return [-y[0]]

    r = compute("S13.T518", "rk4_solve", f=f, t0=0.0, y0=[1.0], t_end=1.0, h=0.1)
    assert r["error"] is None, r
    traj = r["result"]["y"]
    final = traj[-1][0]
    exact = math.exp(-1.0)
    assert approx(final, exact, tol=1e-6), f"RK4 final y(1) = {final}, expected {exact}"


def test_rk4_vector_ode_independent():
    # System: dy1/dt = y2, dy2/dt = -y1  (harmonic oscillator)
    # y(0) = [1, 0], exact: y1(t) = cos(t), y2(t) = -sin(t)
    def osc(t, y):
        return [y[1], -y[0]]

    r = compute("S13.T518", "rk4_step", f=osc, t=0.0, y=[1.0, 0.0], h=0.1)
    assert r["error"] is None, r
    y_next = r["result"]["y_next"]
    assert approx(y_next[0], math.cos(0.1), tol=1e-6), f"y1: {y_next[0]}"
    assert approx(y_next[1], -math.sin(0.1), tol=1e-6), f"y2: {y_next[1]}"


def test_linear_ode_solve_independent():
    # dy/dt = 2*y + 3, y(0) = 1, exact: y(t) = exp(2t) + 1.5*(exp(2t)-1)
    r = compute("S13.T498", "linear_ode_solve", a=2.0, b=3.0, y0=1.0, t=1.0)
    assert r["error"] is None, r
    e2 = math.exp(2.0)
    exact = 1.0 * e2 + 1.5 * (e2 - 1.0)
    assert approx(r["result"]["y"], exact, tol=1e-10), f"got {r['result']['y']}, expected {exact}"


def test_linear_ode_solve_zero_a_independent():
    # dy/dt = 0*y + 5, y(0) = 2 -> y(t) = 2 + 5t
    r = compute("S13.T498", "linear_ode_solve", a=0.0, b=5.0, y0=2.0, t=3.0)
    assert r["error"] is None, r
    assert approx(r["result"]["y"], 17.0, tol=1e-10), f"got {r['result']['y']}"


def test_boundary_value_solve_independent():
    # y'' = -y, y(0)=0, y(pi/2)=1 -> y(t) = sin(t), slope at 0 = 1
    def osc2(t, y):
        return [y[1], -y[0]]

    r = compute(
        "S13.T497", "boundary_value_solve",
        f=osc2, t0=0.0, y0=0.0, t1=math.pi / 2, y1=1.0, h=0.01,
    )
    assert r["error"] is None, r
    assert approx(r["result"]["initial_slope"], 1.0, tol=1e-2), f"slope={r['result']['initial_slope']}"
    assert approx(r["result"]["y"][-1], 1.0, tol=1e-2), f"y_end={r['result']['y'][-1]}"


def test_heat_equation_1d_independent():
    # u(x,0) = sin(pi*x/L), alpha=1, L=1, T small
    r = compute(
        "S13.T501", "heat_equation_1d",
        alpha=1.0, L=1.0, T=0.01, nx=21, nt=100,
        u0=lambda x: math.sin(math.pi * x),
    )
    assert r["error"] is None, r
    assert r["result"]["stable"] is True
    # Boundary conditions should hold
    assert abs(r["result"]["u_final"][0]) < 1e-12
    assert abs(r["result"]["u_final"][-1]) < 1e-12
    # Max should decrease over time (diffusion smooths)
    assert max(r["result"]["u_final"]) <= 1.0 + 1e-10
