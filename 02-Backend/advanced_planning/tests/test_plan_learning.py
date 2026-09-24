
import numpy as np
import pytest
from advanced_planning.plan_learning import Demonstrator, PlanLearner


def test_demonstrator_record():
    d = Demonstrator()
    demo = d.record({"pos": 0}, ["go", "go"], True)
    assert len(d.get_demonstrations()) == 1
    assert demo["length"] == 2


def test_demonstrator_with_context():
    d = Demonstrator()
    d.record({"pos": 0}, ["go"], True, context={"env": "grid"})
    assert d.demonstrations[0]["context"] == {"env": "grid"}


def test_plan_learner_no_demos():
    learner = PlanLearner()
    result = learner.learn_from_demonstrations([])
    assert "error" in result


def test_plan_learner_learn():
    learner = PlanLearner()
    demos = [
        {"initial_state": {"pos": 0}, "actions": ["go", "go"], "outcome": True},
        {"initial_state": {"pos": 0}, "actions": ["go", "go", "go"], "outcome": True},
        {"initial_state": {"pos": 1}, "actions": ["go"], "outcome": True},
    ]
    result = learner.learn_from_demonstrations(demos)
    assert "plan" in result
    assert result["num_demonstrations"] == 3
    assert result["success_rate"] == 1.0


def test_plan_learner_generalize_no_plans():
    learner = PlanLearner()
    result = learner.generalize({"pos": 0})
    assert result is None


def test_plan_learner_generalize():
    learner = PlanLearner()
    demos = [
        {"initial_state": {"pos": 0}, "actions": ["go"], "outcome": True},
    ]
    learner.learn_from_demonstrations(demos)
    plan = learner.generalize({"pos": 1})
    assert plan is not None


def test_plan_learner_similarity():
    learner = PlanLearner()
    state = learner._default_encoder({"x": 1})
    plan = ["go", "stop"]
    sim = learner._similarity(state, plan)
    assert isinstance(sim, float)


def test_plan_learner_avg_length():
    learner = PlanLearner()
    demos = [
        {"initial_state": {}, "actions": ["a", "b"], "outcome": True},
        {"initial_state": {}, "actions": ["a"], "outcome": True},
    ]
    result = learner.learn_from_demonstrations(demos)
    assert abs(result["avg_length"] - 1.5) < 1e-6


def test_plan_learner_skill_library():
    learner = PlanLearner()
    demos = [{"initial_state": {}, "actions": ["a", "b"], "outcome": True}]
    learner.learn_from_demonstrations(demos)
    assert len(learner.skill_library) >= 1
