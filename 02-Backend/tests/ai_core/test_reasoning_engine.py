import numpy as np
from ai_core.reasoning_engine import ReasoningEngine, ProbabilisticInference


def test_forward_chain_basic():
    engine = ReasoningEngine()
    engine.add_fact("a", "A")
    engine.add_fact("b", "B")
    engine.add_rule("r1", ["a", "b"], "c")
    result = engine.infer(method="forward")
    assert "c" in result


def test_forward_chain_no_inference():
    engine = ReasoningEngine()
    engine.add_fact("a", "A")
    engine.add_rule("r1", ["b"], "c")
    result = engine.infer(method="forward")
    assert "c" not in result


def test_backward_chain_satisfiable():
    engine = ReasoningEngine()
    engine.add_fact("a", "A")
    engine.add_rule("r1", ["a"], "b")
    result = engine.infer(method="backward", goal="b")
    assert result["satisfiable"] is True


def test_backward_chain_unsatisfiable():
    engine = ReasoningEngine()
    result = engine.infer(method="backward", goal="z")
    assert result["satisfiable"] is False


def test_abductive_reasoning():
    engine = ReasoningEngine()
    engine.add_rule("r1", ["a"], "b")
    engine.add_fact("a", "A")
    explanations = engine.infer(method="abductive", goal="b")
    assert len(explanations) > 0
    assert explanations[0][0] == "r1"


def test_bayesian_update():
    prob = ProbabilisticInference(n_variables=4)
    prior = np.array([0.25, 0.25, 0.25, 0.25])
    likelihood = np.array([0.9, 0.1, 0.5, 0.5])
    evidence = np.array([1.0, 1.0, 1.0, 1.0])
    posterior = prob.bayesian_update(prior, likelihood, evidence)
    assert np.isclose(np.sum(posterior), 1.0)
    assert posterior[0] > posterior[1]


def test_marginalize():
    prob = ProbabilisticInference(n_variables=4)
    joint = np.ones((4, 4)) / 16
    marginal = prob.marginalize(joint, axis=0)
    assert np.isclose(np.sum(marginal), 1.0)


def test_step_history():
    engine = ReasoningEngine()
    engine.add_fact("a", "A")
    engine.step("a", method="forward")
    assert len(engine.get_history()) == 1
