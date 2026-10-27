import { supabase } from '../supabase'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function getAuthToken() {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token
}

async function request(endpoint, options = {}) {
  const token = await getAuthToken()
  if (!token) {
    throw new Error('No authentication token available')
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}

export async function mathCompute(topicId, operationId, inputs = {}) {
  return request('/v1/math/compute', {
    method: 'POST',
    body: JSON.stringify({
      topic_id: topicId,
      operation_id: operationId,
      inputs,
    }),
  })
}

export async function mathListTopics() {
  return request('/v1/math/topics')
}

export const MATH_OPERATIONS = [
  { topicId: 'S1.T001', name: 'Classify Number', op: 'classify_number' },
  { topicId: 'S1.T002', name: 'Sign Of', op: 'sign_of' },
  { topicId: 'S1.T003', name: 'Is Rational', op: 'is_rational' },
  { topicId: 'S1.T004', name: 'Real Interval Check', op: 'real_interval_check' },
  { topicId: 'S1.T004', name: 'Real Density Between', op: 'real_density_between' },
  { topicId: 'S1.T005', name: 'Complex Basic', op: 'complex_basic' },
  { topicId: 'S1.T005', name: 'Complex Arithmetic', op: 'complex_arithmetic' },
  { topicId: 'S1.T006', name: 'Is Prime', op: 'is_prime' },
  { topicId: 'S1.T006', name: 'Prime Factors', op: 'prime_factors' },
  { topicId: 'S1.T007', name: 'Divisibility Check', op: 'divisibility_check' },
  { topicId: 'S1.T008', name: 'List Factors', op: 'list_factors' },
  { topicId: 'S1.T008', name: 'List Multiples', op: 'list_multiples' },
  { topicId: 'S1.T009', name: 'GCD', op: 'gcd' },
  { topicId: 'S1.T010', name: 'LCM', op: 'lcm' },
  { topicId: 'S1.T011', name: 'Fraction Simplify', op: 'fraction_simplify' },
  { topicId: 'S1.T012', name: 'Decimal Add', op: 'decimal_add' },
  { topicId: 'S1.T012', name: 'Decimal Mul', op: 'decimal_mul' },
  { topicId: 'S1.T013', name: 'Percent to Decimal', op: 'percent_to_decimal' },
  { topicId: 'S1.T013', name: 'Percent Of', op: 'percent_of' },
  { topicId: 'S1.T014', name: 'Ratio Simplify', op: 'ratio_simplify' },
  { topicId: 'S1.T014', name: 'Proportion Solve', op: 'proportion_solve' },
  { topicId: 'S1.T015', name: 'Unit Convert', op: 'unit_convert' },
  { topicId: 'S1.T016', name: 'Power', op: 'power' },
  { topicId: 'S1.T017', name: 'N-th Root', op: 'nth_root' },
  { topicId: 'S1.T018', name: 'Surd Simplify', op: 'surd_simplify' },
  { topicId: 'S1.T019', name: 'Scientific Notation', op: 'scientific_notation' },
  { topicId: 'S1.T020', name: 'Round SigFigs', op: 'round_sigfigs' },
  { topicId: 'S1.T021', name: 'Absolute Value', op: 'absolute' },
  { topicId: 'S1.T022', name: 'Evaluate Expression', op: 'evaluate_expression' },
  { topicId: 'S1.T024', name: 'Dimension Check', op: 'dimension_check' },
  { topicId: 'S1.T025', name: 'Rounding Error', op: 'rounding_error' },
  { topicId: 'S1.T026', name: 'To Base', op: 'to_base' },
  { topicId: 'S1.T026', name: 'From Base', op: 'from_base' },
  { topicId: 'S1.T027', name: 'Modulo', op: 'mod' },
  { topicId: 'S1.T027', name: 'Mod Inverse', op: 'mod_inverse' },
  { topicId: 'S1.T028', name: 'Interval Contains', op: 'interval_contains' },
  { topicId: 'S1.T029', name: 'Factorial', op: 'factorial' },
  { topicId: 'S1.T030', name: 'Summation', op: 'summation' },
  { topicId: 'S2.T040', name: 'Solve Linear', op: 'solve_linear' },
  { topicId: 'S2.T042', name: 'Solve Quadratic', op: 'solve_quadratic' },
  { topicId: 'S2.T034', name: 'Simplify', op: 'simplify' },
  { topicId: 'S2.T035', name: 'Expand', op: 'expand' },
  { topicId: 'S2.T037', name: 'Factor', op: 'factor' },
  { topicId: 'S2.T052', name: 'Solve Log', op: 'solve_log' },
  { topicId: 'S2.T056', name: 'Arithmetic Progression', op: 'arithmetic_progression' },
  { topicId: 'S2.T057', name: 'Geometric Progression', op: 'geometric_progression' },
  { topicId: 'S2.T061', name: 'Permutations', op: 'permutations' },
  { topicId: 'S2.T061', name: 'Combinations', op: 'combinations' },
  { topicId: 'S2.T066', name: 'Group Check', op: 'group_check' },
  { topicId: 'S3.T073', name: 'Linear Function', op: 'linear_function' },
  { topicId: 'S3.T074', name: 'Quadratic Function', op: 'quadratic_function' },
  { topicId: 'S3.T077', name: 'Exponential', op: 'exponential' },
  { topicId: 'S3.T078', name: 'Logarithmic', op: 'logarithmic' },
  { topicId: 'S3.T080', name: 'Composite', op: 'composite' },
  { topicId: 'S3.T081', name: 'Inverse Linear', op: 'inverse_linear' },
  { topicId: 'S3.T083', name: 'Periodic Value', op: 'periodic_value' },
  { topicId: 'S3.T094', name: 'Linear Interpolate', op: 'linear_interpolate' },
  { topicId: 'S3.T096', name: 'Model Assumption', op: 'model_assumption' },
  { topicId: 'S4.T100', name: 'Pythagorean', op: 'pythagorean' },
  { topicId: 'S4.T105', name: 'Distance Point', op: 'distance_point' },
  { topicId: 'S4.T106', name: 'Slope Line', op: 'slope_line' },
  { topicId: 'S4.T112', name: 'Trig', op: 'trig' },
  { topicId: 'S4.T114', name: 'Trig Identity', op: 'trig_identity' },
  { topicId: 'S4.T117', name: 'Radians Convert', op: 'radians_convert' },
  { topicId: 'S4.T118', name: 'Cosine Rule', op: 'cosine_rule' },
  { topicId: 'S4.T121', name: 'Hyperbolic', op: 'hyperbolic' },
  { topicId: 'S4.T124', name: 'Convex Hull', op: 'convex_hull' },
  { topicId: 'S5.T128', name: 'Vector Op', op: 'vector_op' },
  { topicId: 'S5.T129', name: 'Dot Norm', op: 'dot_norm' },
  { topicId: 'S5.T131', name: 'Matrix Mul', op: 'mat_mul' },
  { topicId: 'S5.T132', name: 'Transpose', op: 'transpose' },
  { topicId: 'S5.T132', name: 'Identity', op: 'identity' },
  { topicId: 'S5.T133', name: 'Matrix Inv', op: 'mat_inv' },
  { topicId: 'S5.T134', name: 'Determinant', op: 'determinant' },
  { topicId: 'S5.T135', name: 'Rank', op: 'rank' },
  { topicId: 'S5.T136', name: 'Solve Linear System', op: 'solve_linear_system' },
  { topicId: 'S5.T145', name: 'Eigenvalues', op: 'eig' },
  { topicId: 'S5.T150', name: 'SVD', op: 'svd' },
  { topicId: 'S5.T154', name: 'Matrix Norm', op: 'mat_norm' },
  { topicId: 'S5.T158', name: 'PCA', op: 'pca' },
  { topicId: 'S5.T159', name: 'Low Rank Approx', op: 'low_rank_approx' },
  { topicId: 'S6.T179', name: 'Derivative', op: 'derivative' },
  { topicId: 'S6.T181', name: 'Chain Rule', op: 'chain_rule' },
  { topicId: 'S6.T184', name: 'Partial Derivative', op: 'partial_derivative' },
  { topicId: 'S6.T186', name: 'Gradient', op: 'gradient' },
  { topicId: 'S6.T188', name: 'Hessian', op: 'hessian' },
  { topicId: 'S6.T189', name: 'Taylor Series', op: 'taylor_series' },
  { topicId: 'S6.T196', name: 'Integrate', op: 'integrate' },
  { topicId: 'S6.T215', name: 'Autograd Demo', op: 'autograd_demo' },
  { topicId: 'S7.T222', name: 'Gradient Descent', op: 'gradient_descent' },
  { topicId: 'S7.T229', name: 'Adam Step', op: 'adam_step' },
  { topicId: 'S7.T237', name: 'Lagrange Demo', op: 'lagrange_demo' },
  { topicId: 'S7.T239', name: 'Linear Program Demo', op: 'linear_program_demo' },
  { topicId: 'S7.T242', name: 'Fib DP', op: 'fib_dp' },
  { topicId: 'S7.T252', name: 'Convergence Check', op: 'convergence_check' },
  { topicId: 'S8.T265', name: 'Bayes', op: 'bayes' },
  { topicId: 'S8.T273', name: 'Expectation', op: 'expectation' },
  { topicId: 'S8.T274', name: 'Variance', op: 'variance' },
  { topicId: 'S8.T280', name: 'Bernoulli PMF', op: 'bernoulli_pmf' },
  { topicId: 'S8.T281', name: 'Binomial PMF', op: 'binomial_pmf' },
  { topicId: 'S8.T285', name: 'Normal PDF', op: 'normal_pdf' },
  { topicId: 'S8.T300', name: 'LL Demo', op: 'll_demo' },
  { topicId: 'S8.T301', name: 'CLT Demo', op: 'clt_demo' },
  { topicId: 'S9.T317', name: 'Central Tendency', op: 'central_tendency' },
  { topicId: 'S9.T319', name: 'Sample Variance', op: 'sample_variance' },
  { topicId: 'S9.T327', name: 'CI Mean', op: 'ci_mean' },
  { topicId: 'S9.T328', name: 'Z-Test One Sample', op: 'z_test_one_sample' },
  { topicId: 'S9.T339', name: 'Linear Regression', op: 'linear_regression' },
  { topicId: 'S9.T345', name: 'ANOVA One Way', op: 'anova_one_way' },
  { topicId: 'S10.T378', name: 'Entropy', op: 'entropy' },
  { topicId: 'S10.T383', name: 'Cross Entropy', op: 'cross_entropy' },
  { topicId: 'S10.T384', name: 'KL Divergence', op: 'kl_divergence' },
  { topicId: 'S10.T389', name: 'Perplexity', op: 'perplexity' },
  { topicId: 'S10.T394', name: 'Huffman Lengths', op: 'huffman_lengths' },
  { topicId: 'S11.T426', name: 'Count Permutations', op: 'count_permutations' },
  { topicId: 'S11.T426', name: 'Count Combinations', op: 'count_combinations' },
  { topicId: 'S11.T428', name: 'Pigeonhole', op: 'pigeonhole' },
  { topicId: 'S11.T433', name: 'Dijkstra', op: 'dijkstra' },
  { topicId: 'S11.T454', name: 'Hash Demo', op: 'hash_demo' },
  { topicId: 'S12.T464', name: 'Bisection', op: 'bisection' },
  { topicId: 'S12.T465', name: 'Newton-Raphson', op: 'newton_raphson' },
  { topicId: 'S12.T469', name: 'Trapezoidal', op: 'trapezoidal' },
  { topicId: 'S12.T473', name: 'Gaussian Eliminate', op: 'gaussian_eliminate' },
  { topicId: 'S14.T523', name: 'MSE', op: 'mse' },
  { topicId: 'S14.T523', name: 'Cross Entropy Loss', op: 'cross_entropy_loss' },
  { topicId: 'S14.T531', name: 'L1 Penalty', op: 'l1_penalty' },
  { topicId: 'S14.T531', name: 'L2 Penalty', op: 'l2_penalty' },
  { topicId: 'S14.T534', name: 'K-Fold Split', op: 'kfold_split' },
  { topicId: 'S14.T549', name: 'K-Means One Iter', op: 'kmeans_one_iter' },
  { topicId: 'S15.T577', name: 'Sigmoid', op: 'sigmoid' },
  { topicId: 'S15.T578', name: 'ReLU', op: 'relu' },
  { topicId: 'S15.T580', name: 'Softmax', op: 'softmax' },
  { topicId: 'S15.T585', name: 'Backprop Scalar', op: 'backprop_scalar' },
  { topicId: 'S15.T591', name: 'Batch Norm', op: 'batch_norm' },
  { topicId: 'S15.T618', name: 'LoRA Update', op: 'lora_update' },
  { topicId: 'S16.T643', name: 'Scaled Dot Product Attention', op: 'scaled_dot_product_attention' },
  { topicId: 'S16.T659', name: 'Top-K', op: 'top_k' },
  { topicId: 'S16.T660', name: 'Top-P', op: 'top_p' },
  { topicId: 'S16.T664', name: 'Perplexity', op: 'perplexity' },
  { topicId: 'S16.T679', name: 'Count Params', op: 'count_params' },
  { topicId: 'S16.T681', name: 'Scaling Law', op: 'scaling_law' },
  { topicId: 'S18.T740', name: 'Discounted Return', op: 'discounted_return' },
  { topicId: 'S18.T741', name: 'Bellman Update', op: 'bellman_update' },
  { topicId: 'S18.T752', name: 'Q-Learning Update', op: 'q_learning_update' },
  { topicId: 'S18.T768', name: 'Epsilon Greedy', op: 'epsilon_greedy' },
  { topicId: 'S19.T781', name: 'Interval Measure', op: 'interval_measure' },
  { topicId: 'S19.T803', name: 'Wasserstein 1D', op: 'wasserstein_1d' },
  { topicId: 'S19.T841', name: 'DP Laplace Scale', op: 'dp_laplace_scale' },
  { topicId: 'S19.T850', name: 'Verify Bound', op: 'verify_bound' },
]

export function getMathOperations() {
  return MATH_OPERATIONS.map(({ topicId, name, op }) => ({
    topicId,
    operationId: op,
    name,
  }))
}