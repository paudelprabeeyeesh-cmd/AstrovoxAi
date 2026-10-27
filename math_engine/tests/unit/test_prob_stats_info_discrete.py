"""Unit tests for Sections 8-11 probability, statistics, info theory, discrete."""

from math_engine.probability.distributions import (
    bayes, expectation, variance, bernoulli_pmf, binomial_pmf, normal_pdf,
    ll_demo, clt_demo,
)
from math_engine.statistics.descriptive import (
    central_tendency, sample_variance, ci_mean, z_test_one_sample,
    linear_regression, anova_one_way,
)
from math_engine.information_theory.entropy import (
    entropy, cross_entropy, kl_divergence, perplexity, huffman_lengths,
)
from math_engine.discrete.logic import (
    count_permutations, count_combinations, pigeonhole, dijkstra, hash_demo,
)


def test_bayes():
    r = bayes(0.01, 0.9, 0.1)
    assert 0 < r.result["p_a_given_b"] < 1


def test_bernoulli_binomial():
    assert bernoulli_pmf(1, 0.5).result["pmf"] == 0.5
    assert abs(binomial_pmf(2, 4, 0.5).result["pmf"] - 0.375) < 1e-9


def test_normal_pdf():
    r = normal_pdf(0, 0, 1)
    assert abs(r.result["pdf"] - 0.39894) < 1e-4


def test_stats():
    assert central_tendency([1, 2, 3]).result["mean"] == 2.0
    assert linear_regression([1, 2, 3], [2, 4, 6]).result["r_squared"] > 0.99
    assert anova_one_way(groups=[[1, 2], [3, 4]]).error is None


def test_info_theory():
    assert abs(entropy([0.5, 0.5]).result["entropy"] - 1.0) < 1e-9
    assert kl_divergence([0.5, 0.5], [0.5, 0.5]).result["kl_divergence"] == 0.0
    assert perplexity([0.5, 0.5]).result["perplexity"] == 2.0


def test_discrete():
    assert count_permutations(5, 2).result == 20
    assert count_combinations(5, 2).result == 10
    assert pigeonhole(10, 3).result["guaranteed_collision"] is True
    g = {"A": {"B": 1, "C": 4}, "B": {"C": 2}, "C": {}}
    assert dijkstra(g, "A", "C").result["distance"] == 3.0
