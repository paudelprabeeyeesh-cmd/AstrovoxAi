import numpy as np
import pytest
from reasoning_engine.self_consistency import SelfConsistency


def test_generate_multiple_answers():
    sc = SelfConsistency(generate_fn=lambda q: f"ans_{q}", num_samples=5)
    answers = sc.generate_multiple_answers("q1")
    assert len(answers) == 5
    assert all(a == "ans_q1" for a in answers)


def test_majority_vote():
    sc = SelfConsistency(generate_fn=lambda q: "same")
    ans, conf = sc.majority_vote(["a", "a", "b", "a"])
    assert ans == "a"
    assert conf == 0.75


def test_majority_vote_empty():
    sc = SelfConsistency(generate_fn=lambda q: "same")
    ans, conf = sc.majority_vote([])
    assert ans == ""
    assert conf == 0.0


def test_semantic_cluster_identical():
    sc = SelfConsistency(generate_fn=lambda q: "same", similarity_threshold=0.5)
    clusters = sc.semantic_cluster(["a", "a", "a"])
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_semantic_cluster_distinct():
    sc = SelfConsistency(generate_fn=lambda q: "same", similarity_threshold=0.99)
    clusters = sc.semantic_cluster(["a", "b"])
    assert len(clusters) == 2


def test_run_returns_tuple():
    sc = SelfConsistency(generate_fn=lambda q: "fixed", num_samples=3, similarity_threshold=0.5)
    ans, conf, clusters = sc.run("q")
    assert isinstance(ans, str)
    assert 0.0 <= conf <= 1.0
    assert isinstance(clusters, list)


def test_run_with_varied_answers():
    answers = ["a", "a", "b", "a", "b"]
    sc = SelfConsistency(generate_fn=lambda q: answers.pop(), num_samples=len(answers), similarity_threshold=0.99)
    ans, conf, clusters = sc.run("q")
    assert ans == "a"
    assert conf > 0.5


def test_cosine_similarity_properties():
    sc = SelfConsistency(generate_fn=lambda q: "same")
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    sim = sc._cosine_similarity(a, b)
    assert abs(sim - 1.0) < 1e-6

    c = np.array([0.0, 1.0, 0.0])
    sim2 = sc._cosine_similarity(a, c)
    assert abs(sim2 - 0.0) < 1e-6
