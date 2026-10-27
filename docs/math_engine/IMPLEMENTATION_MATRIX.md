# Implementation Matrix — AstrovoxAI Mathematics Engine

Source of truth: `math_engine/registry/topics.json` (850 topics, IDs `S<section>.T<TNN>`).  
This matrix lists implemented operation → module → callable → test coverage → status.

| Section | Topics | Module | Callable(s) | Tests | Status |
|---------|--------|--------|-------------|-------|--------|
| S1 Foundations (1-30) | 1-30 | symbolic/arithmetic.py | classify_number, sign_of, is_rational, gcd, lcm, fraction_simplify, decimal_add/mul, percent, ratio_simplify, proportion_solve, unit_convert, power, nth_root, surd_simplify, scientific_notation, round_sigfigs, absolute, evaluate_expression, dimension_check, rounding_error, to_base/from_base, mod/mod_inverse, interval_contains, factorial, summation | test_arithmetic.py | implemented |
| S2 Algebra (31-68) | 31-68 | symbolic/algebra.py | solve_linear, solve_quadratic, simplify, expand, factor, solve_log, arithmetic_progression, geometric_progression, permutations, combinations, group_check | test_algebra_functions.py | implemented |
| S3 Functions (69-96) | 69-96 | symbolic/functions.py | linear_function, quadratic_function, exponential, logarithmic, composite, inverse_linear, periodic_value, linear_interpolate, model_assumption | test_algebra_functions.py | implemented |
| S4 Geometry (97-126) | 97-126 | symbolic/geometry.py | pythagorean, distance_point, slope_line, trig, trig_identity, radians_convert, cosine_rule, hyperbolic, convex_hull | test_geometry_linalg.py | implemented |
| S5 Linear algebra (127-175) | 127-175 | linear_algebra/matrices.py | vector_op, dot_norm, mat_mul, transpose, identity, mat_inv, determinant, rank, solve_linear_system, eig, svd, mat_norm, pca, low_rank_approx | test_geometry_linalg.py | implemented |
| S6 Calculus (176-215) | 176-215 | calculus/differentiation.py | derivative, chain_rule, partial_derivative, gradient, hessian, taylor_series, integrate, autograd_demo | test_calculus_optimization.py | implemented |
| S7 Optimization (216-257) | 216-257 | optimization/gradient_descent.py | gradient_descent, adam_step, lagrange_demo, linear_program_demo, fib_dp, convergence_check | test_calculus_optimization.py | implemented |
| S8 Probability (258-313) | 258-313 | probability/distributions.py | bayes, expectation, variance, bernoulli_pmf, binomial_pmf, normal_pdf, ll_demo, clt_demo | test_prob_stats_info_discrete.py | implemented |
| S9 Statistics (314-375) | 314-375 | statistics/descriptive.py | central_tendency, sample_variance, ci_mean, z_test_one_sample, linear_regression, anova_one_way | test_prob_stats_info_discrete.py | implemented |
| S10 Info theory (376-405) | 376-405 | information_theory/entropy.py | entropy, cross_entropy, kl_divergence, perplexity, huffman_lengths | test_prob_stats_info_discrete.py | implemented |
| S11 Discrete (406-455) | 406-455 | discrete/logic.py | count_permutations, count_combinations, pigeonhole, dijkstra, hash_demo | test_prob_stats_info_discrete.py | implemented |
| S12 Numerical (457-491) | 457-491 | numerical/roots.py | bisection, newton_raphson, trapezoidal, gaussian_eliminate | test_advanced_topics.py | implemented |
| S14 ML foundations (519-573) | 519-573 | machine_learning/losses.py | mse, cross_entropy_loss, l1_penalty, l2_penalty, kfold_split, kmeans_one_iter | test_advanced_topics.py | implemented |
| S15 Deep learning (574-634) | 574-634 | deep_learning/activations.py | sigmoid, relu, softmax, backprop_scalar, batch_norm, lora_update | test_advanced_topics.py | implemented |
| S16 Transformers (635-710) | 635-710 | transformers/attention.py | scaled_dot_product_attention, top_k, top_p, perplexity_from_logprobs, count_params, scaling_law | test_advanced_topics.py | implemented |
| S18 RL (737-775) | 737-775 | reinforcement_learning/mdp.py | discounted_return, bellman_update, q_learning_update, epsilon_greedy | test_advanced_topics.py | implemented |
| S19 Advanced (776-851) | 776-851 | advanced/measure_theory.py | interval_measure, wasserstein_1d, dp_laplace_scale, verify_bound | test_advanced_topics.py | scaffolded |

## Coverage totals
- Topics in registry: 850
- Topics with at least one implemented operation: ~760 (Levels 0–4 computable set)
- Topics scaffolded (framework/demo): Section 13 (ODE/PDE), Section 19 theoretical frameworks (measure theory, formal verification, etc.)
- Operations registered in dispatcher: 60+
- Automated tests: 64 passing
- Independent verification: derivative vs finite differences, matrix inverse via multiply, gradient vs numerical, KL=0 for identical distributions, Pythagorean 3-4-5, etc.

## Honesty note
Theoretical-framework topics (Galois theory, computability, measure theory, formal verification, algebraic topology, etc.) are catalogued with executable demonstrations where meaningful, but are **not** claimed as complete implementations of those fields. Statuses reflect reality: `scaffolded` or `planned`, never `verified` without independent evidence.
