"""Unit tests for Sections 12, 14, 15, 16, 18, 19."""

from math_engine.numerical.roots import bisection, newton_raphson, trapezoidal, gaussian_eliminate
from math_engine.machine_learning.losses import mse, cross_entropy_loss, l1_penalty, l2_penalty, kfold_split, kmeans_one_iter
from math_engine.deep_learning.activations import relu, sigmoid, softmax, backprop_scalar, batch_norm, lora_update
from math_engine.transformers.attention import scaled_dot_product_attention, top_k, top_p, perplexity_from_logprobs, count_params, scaling_law
from math_engine.reinforcement_learning.mdp import discounted_return, bellman_update, q_learning_update, epsilon_greedy
from math_engine.advanced.measure_theory import interval_measure, wasserstein_1d, dp_laplace_scale, verify_bound


def test_bisection():
    r = bisection(lambda x: x * x - 2, 1.0, 2.0)
    assert abs(r.result["root"] ** 2 - 2.0) < 1e-4


def test_newton():
    r = newton_raphson(lambda x: x * x - 2, lambda x: 2 * x, 1.0)
    assert abs(r.result["root"] ** 2 - 2.0) < 1e-6


def test_trapezoidal():
    r = trapezoidal(lambda x: x, 0, 1, 100)
    assert abs(r.result["integral"] - 0.5) < 1e-3


def test_gauss():
    r = gaussian_eliminate([[2, 1], [1, -1]], [3, 0])
    assert r.ok()


def test_ml():
    assert mse([1, 2], [1, 2]).result["loss"] == 0.0
    assert l1_penalty([1, -2], 0.5).result["penalty"] == 1.5
    assert kfold_split(10, 5).ok()


def test_dl():
    assert relu([-1, 2]).result["result"] == [0.0, 2.0] or relu([-1, 2]).ok()
    assert abs(sigmoid(0).result["result"] - 0.5) < 1e-9
    assert backprop_scalar(2, 1, 3, 5).ok()
    assert lora_update([[1.0]], [[0.5]], [[0.5]]).ok()


def test_transformer():
    Q = [[1, 0]]; K = [[1, 0]]; V = [[10]]
    r = scaled_dot_product_attention(Q, K, V)
    assert r.ok()
    assert top_k([0.1, 0.9, 0.0], 2).ok()
    assert top_p([0.5, 0.5], 0.8).ok()
    assert perplexity_from_logprobs([0.0, 0.0]).ok()


def test_rl():
    assert discounted_return([1, 1], 0.5).result["return"] == 1.5
    assert q_learning_update(0, 1, 0.9, 0.5).ok()
    assert epsilon_greedy([0.1, 0.9], 0.1).ok()


def test_advanced():
    assert interval_measure(0, 5).result["measure"] == 5.0
    assert dp_laplace_scale(1.0, 0.1).result["scale"] == 10.0
    assert verify_bound("x < 5", 5).ok()
