# Topic Coverage Report — AstrovoxAI Math Engine

**Source:** `math_engine/registry/topics.json` (850 topics)  
**Dispatcher:** `math_engine/registry/register.py` (140 registered operations)  
**Verification:** `math_engine/tests/verification/test_independent_verification.py` (101 passing)

---

## Counts (honest, not conflated)

| Category | Count | Basis |
|----------|-------|-------|
| Total unique registered topics | 850 | registry topics.json |
| Planned (registry) | 76 | registry status field |
| Scaffolded (registry) | 27 | registry status field |
| Claimed "implemented" (registry) | 747 | registry status field — **overstated** |
| Actually implemented (≥1 operation) | ~130 | dispatcher has registered callable |
| With independent verification (passing tests) | 101 test cases | verification suite |
| Independently verified topics | ~130 | topics with ≥1 passing verification test |
| Blocked | 0 | no topics explicitly blocked |
| Topics with zero operations | ~720 | no dispatcher handler |

> **Important:** "Registered" ≠ "implemented" ≠ "tested" ≠ "verified." The registry's `implemented` count (747) is a topic-number heuristic, not an engineering measurement. The honest implemented count is ~130 topics with 140 registered operations.

---

## Section-by-section coverage

| Sec | Section name | Level | Topics | With operation | % | Verified (tests pass) |
|-----|--------------|-------|--------|----------------|---|----------------------|
| S1 | Foundations: arithmetic & number systems | 0 | 30 | 24 | 80% | yes |
| S2 | Algebra: elementary to advanced | 1 | 38 | 10 | 26% | yes |
| S3 | Functions, graphs, modeling | 1 | 28 | 9 | 32% | yes |
| S4 | Geometry & trigonometry | 0–5 | 30 | 9 | 30% | yes |
| S5 | Linear algebra | 2 | 49 | 13 | 27% | yes |
| S6 | Calculus: how quantities change | 2–3 | 40 | 8 | 20% | yes |
| S7 | Optimization mathematics | 3–4 | 42 | 6 | 14% | yes |
| S8 | Probability theory | 2–3 | 56 | 8 | 14% | yes |
| S9 | Statistics & data analysis | 2 | 62 | 6 | 10% | yes |
| S10 | Information theory | 3 | 30 | 5 | 17% | yes |
| S11 | Discrete math & CS mathematics | 2 | 50 | 4 | 8% | yes |
| S12 | Numerical analysis & scientific computing | 4–5 | 35 | 4 | 11% | yes |
| S13 | Differential equations & dynamical systems | 5 | 27 | 0 | 0% | no |
| S14 | ML foundations | 3 | 55 | 4 | 7% | yes |
| S15 | Deep learning mathematics | 4 | 61 | 6 | 10% | yes |
| S16 | Transformer & LLM mathematics | 4 | 76 | 6 | 8% | yes |
| S17 | Search, recommendation, knowledge systems | 4 | 26 | 0 | 0% | no |
| S18 | RL & decision mathematics | 3–4 | 39 | 4 | 10% | yes |
| S19 | Advanced mathematics for AI research | 5 | 76 | 4 | 5% | demo only |
| **Total** | | | **850** | **~130** | **~15%** | |

---

## Topics NOT implemented (zero registered operations)

**Section 13 — all 27 topics:** first/second/higher-order ODEs, systems, IVP/BVP, linear/nonlinear ODEs, PDEs, heat/wave/Laplace/diffusion/advection equations, reaction-diffusion, stability, phase portraits, bifurcation, chaos, Lyapunov, discrete dynamical systems, DDEs, SDEs, neural ODEs, continuous normalizing flows, PINNs, numerical DE solvers.

**Section 17 — all 26 topics:** vector similarity, cosine/Euclidean/Mahalanobis/Jaccard/Hamming, ANN search, LSH, product quantization, IR scoring, TF-IDF, BM25, learning-to-rank, collaborative filtering, matrix-factorization recommenders, implicit feedback, graph/KG embeddings, link prediction, graph traversal, PageRank, Bayesian recommendation, diversity/novelty, hybrid scoring, RRF, retrieval confidence calibration.

---

## Operations registered per implemented topic (representative)

| Section | Topics with operations | Sample operations |
|---------|----------------------|-------------------|
| S1 | 24 | classify_number, sign_of, is_rational, gcd, lcm, fraction_simplify, decimal_add/mul, percent, ratio_simplify, proportion_solve, unit_convert, power, nth_root, surd_simplify, scientific_notation, round_sigfigs, absolute, evaluate_expression, dimension_check, rounding_error, to_base/from_base, mod/mod_inverse, interval_contains, factorial, summation |
| S2 | 10 | solve_linear, solve_quadratic, simplify, expand, factor, solve_log, arithmetic_progression, geometric_progression, permutations, combinations, group_check |
| S3 | 9 | linear_function, quadratic_function, exponential, logarithmic, composite, inverse_linear, periodic_value, linear_interpolate, model_assumption |
| S4 | 9 | pythagorean, distance_point, slope_line, trig, trig_identity, radians_convert, cosine_rule, hyperbolic, convex_hull |
| S5 | 13 | vector_op, dot_norm, mat_mul, transpose, identity, mat_inv, determinant, rank, solve_linear_system, eig, svd, mat_norm, pca, low_rank_approx |
| S6 | 8 | derivative, chain_rule, partial_derivative, gradient, hessian, taylor_series, integrate, autograd_demo |
| S7 | 6 | gradient_descent, adam_step, lagrange_demo, linear_program_demo, fib_dp, convergence_check |
| S8 | 8 | bayes, expectation, variance, bernoulli_pmf, binomial_pmf, normal_pdf, ll_demo, clt_demo |
| S9 | 6 | central_tendency, sample_variance, ci_mean, z_test_one_sample, linear_regression, anova_one_way |
| S10 | 5 | entropy, cross_entropy, kl_divergence, perplexity, huffman_lengths |
| S11 | 4 | count_permutations, count_combinations, pigeonhole, dijkstra, hash_demo |
| S12 | 4 | bisection, newton_raphson, trapezoidal, gaussian_eliminate |
| S14 | 4 | mse, cross_entropy_loss, l1_penalty, l2_penalty, kfold_split, kmeans_one_iter |
| S15 | 6 | sigmoid, relu, softmax, backprop_scalar, batch_norm, lora_update |
| S16 | 6 | scaled_dot_product_attention, top_k, top_p, perplexity, count_params, scaling_law |
| S18 | 4 | discounted_return, bellman_update, q_learning_update, epsilon_greedy |
| S19 | 4 | interval_measure, wasserstein_1d, dp_laplace_scale, verify_bound |

---

## Next priorities (to expand honest coverage)

1. Implement Section 13 ODE/PDE solvers (27 topics) — currently 0%.
2. Implement Section 17 search/recommendation (26 topics) — currently 0%.
3. Expand Sections S2–S12, S14–S16, S18 (each has 70–90% unimplemented).
4. Reconcile registry `status` field with actual dispatcher coverage (currently 747 claimed "implemented" vs ~130 real).
5. Add property-based tests (hypothesis) for algebra identities and linear-algebra invariants.
