import numpy as np
from ai_core.decision_making import DecisionMaker, UtilityFunction, Outcome, MarkovDecisionProcess


def test_utility_evaluate_expected():
    util = UtilityFunction(risk_aversion=0.0)
    outcomes = [
        Outcome(description="win", utility=10.0, probability=0.5),
        Outcome(description="lose", utility=-5.0, probability=0.5),
    ]
    score = util.evaluate(outcomes)
    expected = 0.5 * 10.0 + 0.5 * (-5.0)
    assert np.isclose(score, expected)


def test_utility_risk_penalty():
    util = UtilityFunction(risk_aversion=1.0)
    outcomes = [
        Outcome(description="a", utility=0.0, probability=0.5),
        Outcome(description="b", utility=10.0, probability=0.5),
    ]
    score = util.evaluate(outcomes)
    assert score < util.expected_value(outcomes)


def test_decision_tree_optimal_choice():
    dm = DecisionMaker(risk_aversion=0.0)
    choice = dm.choose(
        "d1",
        ["safe", "risky"],
        {
            "safe": [Outcome("s", utility=5.0, probability=1.0)],
            "risky": [Outcome("r_win", utility=20.0, probability=0.5),
                      Outcome("r_lose", utility=-2.0, probability=0.5)],
        },
    )
    assert choice in {"safe", "risky"}
    assert len(dm.get_decision_log()) == 1


def test_mdp_value_iteration():
    mdp = MarkovDecisionProcess(n_states=2, n_actions=2, discount=0.9)
    mdp.set_transition(0, 0, 0, 1.0)
    mdp.set_reward(0, 0, 0, 1.0)
    mdp.set_transition(0, 1, 1, 1.0)
    mdp.set_reward(0, 1, 1, 5.0)
    mdp.set_transition(1, 0, 1, 1.0)
    mdp.set_transition(1, 1, 1, 1.0)
    values = mdp.value_iteration(tol=1e-6)
    assert values.shape == (2,)
    assert all(np.isfinite(v) for v in values)
    assert values[0] > 0.0
    assert np.argmax(values) == 0
