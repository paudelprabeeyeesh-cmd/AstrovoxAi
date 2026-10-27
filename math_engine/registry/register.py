"""Register all math engine operations with the dispatcher."""

from __future__ import annotations

from math_engine.core.dispatcher import Dispatcher
from math_engine.core.result import MathResult
from math_engine.core.errors import UnsupportedTopicError


def build_dispatcher() -> Dispatcher:
    d = Dispatcher()

    # ---- Section 1: Arithmetic ----
    from math_engine.symbolic import arithmetic as A
    d.register("S1.T001", "classify_number", A.classify_number)
    d.register("S1.T002", "sign_of", A.sign_of)
    d.register("S1.T003", "is_rational", A.is_rational)
    d.register("S1.T004", "real_interval_check", A.real_interval_check)
    d.register("S1.T004", "real_density_between", A.real_density_between)
    d.register("S1.T005", "complex_basic", A.complex_basic)
    d.register("S1.T005", "complex_arithmetic", A.complex_arithmetic)
    d.register("S1.T006", "is_prime", A.is_prime)
    d.register("S1.T006", "prime_factors", A.prime_factors)
    d.register("S1.T007", "divisibility_check", A.divisibility_check)
    d.register("S1.T008", "list_factors", A.list_factors)
    d.register("S1.T008", "list_multiples", A.list_multiples)
    d.register("S1.T009", "gcd", A.gcd)
    d.register("S1.T010", "lcm", A.lcm)
    d.register("S1.T011", "fraction_simplify", A.fraction_simplify)
    d.register("S1.T012", "decimal_add", A.decimal_add)
    d.register("S1.T012", "decimal_mul", A.decimal_mul)
    d.register("S1.T013", "percent_to_decimal", A.percent)
    d.register("S1.T013", "percent_of", A.percent)
    d.register("S1.T014", "ratio_simplify", A.ratio_simplify)
    d.register("S1.T014", "proportion_solve", A.proportion_solve)
    d.register("S1.T015", "unit_convert", A.unit_convert)
    d.register("S1.T016", "power", A.power)
    d.register("S1.T017", "nth_root", A.nth_root)
    d.register("S1.T018", "surd_simplify", A.surd_simplify)
    d.register("S1.T019", "scientific_notation", A.scientific_notation)
    d.register("S1.T020", "round_sigfigs", A.round_sigfigs)
    d.register("S1.T021", "absolute", A.absolute)
    d.register("S1.T022", "evaluate_expression", A.evaluate_expression)
    d.register("S1.T024", "dimension_check", A.dimension_check)
    d.register("S1.T025", "rounding_error", A.rounding_error)
    d.register("S1.T026", "to_base", A.to_base)
    d.register("S1.T026", "from_base", A.from_base)
    d.register("S1.T027", "mod", A.mod)
    d.register("S1.T027", "mod_inverse", A.mod_inverse)
    d.register("S1.T028", "interval_contains", A.interval_contains)
    d.register("S1.T029", "factorial", A.factorial)
    d.register("S1.T030", "summation", A.summation)

    # ---- Section 2: Algebra ----
    from math_engine.symbolic import algebra as Alg
    d.register("S2.T040", "solve_linear", Alg.solve_linear)
    d.register("S2.T042", "solve_quadratic", Alg.solve_quadratic)
    d.register("S2.T034", "simplify", Alg.simplify_expression)
    d.register("S2.T035", "expand", Alg.expand_expression)
    d.register("S2.T037", "factor", Alg.factor_expression)
    d.register("S2.T052", "solve_log", Alg.solve_log)
    d.register("S2.T056", "arithmetic_progression", Alg.arithmetic_progression)
    d.register("S2.T057", "geometric_progression", Alg.geometric_progression)
    d.register("S2.T061", "permutations", Alg.permutations)
    d.register("S2.T061", "combinations", Alg.combinations)
    d.register("S2.T066", "group_check", Alg.group_check)

    # ---- Section 3: Functions ----
    from math_engine.symbolic import functions as Fn
    d.register("S3.T073", "linear_function", Fn.linear_function)
    d.register("S3.T074", "quadratic_function", Fn.quadratic_function)
    d.register("S3.T077", "exponential", Fn.exponential)
    d.register("S3.T078", "logarithmic", Fn.logarithmic)
    d.register("S3.T080", "composite", Fn.composite)
    d.register("S3.T081", "inverse_linear", Fn.inverse_linear)
    d.register("S3.T083", "periodic_value", Fn.periodic_value)
    d.register("S3.T094", "linear_interpolate", Fn.linear_interpolate)
    d.register("S3.T096", "model_assumption", Fn.model_assumption)

    # ---- Section 4: Geometry ----
    from math_engine.symbolic import geometry as G
    d.register("S4.T100", "pythagorean", G.pythagorean)
    d.register("S4.T105", "distance_point", G.distance_point)
    d.register("S4.T106", "slope_line", G.slope_line)
    d.register("S4.T112", "trig", G.trig)
    d.register("S4.T114", "trig_identity", G.trig_identity)
    d.register("S4.T117", "radians_convert", G.radians_convert)
    d.register("S4.T118", "cosine_rule", G.cosine_rule)
    d.register("S4.T121", "hyperbolic", G.hyperbolic)
    d.register("S4.T124", "convex_hull", G.convex_hull)

    # ---- Section 5: Linear algebra ----
    from math_engine.linear_algebra import matrices as LA
    d.register("S5.T128", "vector_op", LA.vector_op)
    d.register("S5.T129", "dot_norm", LA.dot_norm)
    d.register("S5.T131", "mat_mul", LA.mat_mul)
    d.register("S5.T132", "transpose", LA.transpose)
    d.register("S5.T132", "identity", LA.identity)
    d.register("S5.T133", "mat_inv", LA.mat_inv)
    d.register("S5.T134", "determinant", LA.determinant)
    d.register("S5.T135", "rank", LA.rank)
    d.register("S5.T136", "solve_linear_system", LA.solve_linear_system)
    d.register("S5.T145", "eig", LA.eig)
    d.register("S5.T150", "svd", LA.svd)
    d.register("S5.T154", "mat_norm", LA.mat_norm)
    d.register("S5.T158", "pca", LA.pca)
    d.register("S5.T159", "low_rank_approx", LA.low_rank_approx)

    # ---- Section 6: Calculus ----
    from math_engine.calculus import differentiation as Calc
    d.register("S6.T179", "derivative", Calc.derivative)
    d.register("S6.T181", "chain_rule", Calc.chain_rule)
    d.register("S6.T184", "partial_derivative", Calc.partial_derivative)
    d.register("S6.T186", "gradient", Calc.gradient)
    d.register("S6.T188", "hessian", Calc.hessian)
    d.register("S6.T189", "taylor_series", Calc.taylor_series)
    d.register("S6.T196", "integrate", Calc.integrate)
    d.register("S6.T215", "autograd_demo", Calc.autograd_demo)

    # ---- Section 7: Optimization ----
    from math_engine.optimization import gradient_descent as Opt
    d.register("S7.T222", "gradient_descent", Opt.gradient_descent)
    d.register("S7.T229", "adam_step", Opt.adam_step)
    d.register("S7.T237", "lagrange_demo", Opt.lagrange_demo)
    d.register("S7.T239", "linear_program_demo", Opt.linear_program_demo)
    d.register("S7.T242", "fib_dp", Opt.fib_dp)
    d.register("S7.T252", "convergence_check", Opt.convergence_check)

    # ---- Section 8: Probability ----
    from math_engine.probability import distributions as P
    d.register("S8.T265", "bayes", P.bayes)
    d.register("S8.T273", "expectation", P.expectation)
    d.register("S8.T274", "variance", P.variance)
    d.register("S8.T280", "bernoulli_pmf", P.bernoulli_pmf)
    d.register("S8.T281", "binomial_pmf", P.binomial_pmf)
    d.register("S8.T285", "normal_pdf", P.normal_pdf)
    d.register("S8.T300", "ll_demo", P.ll_demo)
    d.register("S8.T301", "clt_demo", P.clt_demo)

    # ---- Section 9: Statistics ----
    from math_engine.statistics import descriptive as Stat
    d.register("S9.T317", "central_tendency", Stat.central_tendency)
    d.register("S9.T319", "sample_variance", Stat.sample_variance)
    d.register("S9.T327", "ci_mean", Stat.ci_mean)
    d.register("S9.T328", "z_test_one_sample", Stat.z_test_one_sample)
    d.register("S9.T339", "linear_regression", Stat.linear_regression)
    d.register("S9.T345", "anova_one_way", Stat.anova_one_way)

    # ---- Section 10: Information theory ----
    from math_engine.information_theory import entropy as IT
    d.register("S10.T378", "entropy", IT.entropy)
    d.register("S10.T383", "cross_entropy", IT.cross_entropy)
    d.register("S10.T384", "kl_divergence", IT.kl_divergence)
    d.register("S10.T389", "perplexity", IT.perplexity)
    d.register("S10.T394", "huffman_lengths", IT.huffman_lengths)

    # ---- Section 11: Discrete ----
    from math_engine.discrete import logic as D
    d.register("S11.T426", "count_permutations", D.count_permutations)
    d.register("S11.T426", "count_combinations", D.count_combinations)
    d.register("S11.T428", "pigeonhole", D.pigeonhole)
    d.register("S11.T433", "dijkstra", D.dijkstra)
    d.register("S11.T454", "hash_demo", D.hash_demo)

    # ---- Section 12: Numerical ----
    from math_engine.numerical import roots as Num
    d.register("S12.T464", "bisection", Num.bisection)
    d.register("S12.T465", "newton_raphson", Num.newton_raphson)
    d.register("S12.T469", "trapezoidal", Num.trapezoidal)
    d.register("S12.T473", "gaussian_eliminate", Num.gaussian_eliminate)

    # ---- Section 13: ODE Initial-Value Problems ----
    from math_engine.numerical import ode as ODE
    d.register("S13.T496", "euler_step", ODE.euler_step)
    d.register("S13.T496", "euler_solve", ODE.euler_solve)
    d.register("S13.T518", "rk4_step", ODE.rk4_step)
    d.register("S13.T518", "rk4_solve", ODE.rk4_solve)
    d.register("S13.T498", "linear_ode_solve", ODE.linear_ode_solve)
    d.register("S13.T497", "boundary_value_solve", ODE.boundary_value_solve)
    d.register("S13.T501", "heat_equation_1d", ODE.heat_equation_1d)

    # ---- Section 14: ML foundations ----
    from math_engine.machine_learning import losses as ML
    d.register("S14.T523", "mse", ML.mse)
    d.register("S14.T523", "cross_entropy_loss", ML.cross_entropy_loss)
    d.register("S14.T531", "l1_penalty", ML.l1_penalty)
    d.register("S14.T531", "l2_penalty", ML.l2_penalty)
    d.register("S14.T534", "kfold_split", ML.kfold_split)
    d.register("S14.T549", "kmeans_one_iter", ML.kmeans_one_iter)

    # ---- Section 15: Deep learning ----
    from math_engine.deep_learning import activations as DL
    d.register("S15.T577", "sigmoid", DL.sigmoid)
    d.register("S15.T578", "relu", DL.relu)
    d.register("S15.T580", "softmax", DL.softmax)
    d.register("S15.T585", "backprop_scalar", DL.backprop_scalar)
    d.register("S15.T591", "batch_norm", DL.batch_norm)
    d.register("S15.T618", "lora_update", DL.lora_update)

    # ---- Section 16: Transformers ----
    from math_engine.transformers import attention as Tr
    d.register("S16.T643", "scaled_dot_product_attention", Tr.scaled_dot_product_attention)
    d.register("S16.T659", "top_k", Tr.top_k)
    d.register("S16.T660", "top_p", Tr.top_p)
    d.register("S16.T664", "perplexity", Tr.perplexity_from_logprobs)
    d.register("S16.T679", "count_params", Tr.count_params)
    d.register("S16.T681", "scaling_law", Tr.scaling_law)

    # ---- Section 18: RL ----
    from math_engine.reinforcement_learning import mdp as RL
    d.register("S18.T740", "discounted_return", RL.discounted_return)
    d.register("S18.T741", "bellman_update", RL.bellman_update)
    d.register("S18.T752", "q_learning_update", RL.q_learning_update)
    d.register("S18.T768", "epsilon_greedy", RL.epsilon_greedy)

    # ---- Section 19: Advanced ----
    from math_engine.advanced import measure_theory as Adv
    d.register("S19.T781", "interval_measure", Adv.interval_measure)
    d.register("S19.T803", "wasserstein_1d", Adv.wasserstein_1d)
    d.register("S19.T841", "dp_laplace_scale", Adv.dp_laplace_scale)
    d.register("S19.T850", "verify_bound", Adv.verify_bound)

    return d
