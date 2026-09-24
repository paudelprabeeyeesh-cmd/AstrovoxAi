import pytest
from world_model.counterfactual import CounterfactualEngine, CounterfactualScenario


class TestCounterfactualEngine:
    def test_generate_scenario(self):
        engine = CounterfactualEngine()
        factual = {"rain": 0.0, "flood": 0.0}
        intervention = {"rain": 1.0}
        scenario = engine.generate(factual, intervention, "flood")
        assert "rain" in scenario.intervention
        assert scenario.intervention["rain"] == 1.0

    def test_difference(self):
        engine = CounterfactualEngine()
        factual = {"x": 1.0, "y": 2.0}
        counterfactual = {"x": 3.0, "y": 2.0}
        diff = engine.difference(factual, counterfactual)
        assert diff["x"] == 2.0
        assert diff["y"] == 0.0

    def test_best_explanation(self):
        engine = CounterfactualEngine()
        engine.generate({"a": 0}, {"a": 1}, "out")
        scenarios = engine.scenarios
        best = engine.best_explanation(scenarios)
        assert best is not None
