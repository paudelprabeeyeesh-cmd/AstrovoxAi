import pytest
from mental_simulation.imagination import ImaginationEngine, Scenario


class TestImaginationEngine:
    def test_generate_scenarios(self):
        engine = ImaginationEngine(seed=42)
        scenarios = engine.generate("explore", {"setting": "forest"}, n=3)
        assert len(scenarios) == 3
        assert all(isinstance(s, Scenario) for s in scenarios)

    def test_plausibility_range(self):
        engine = ImaginationEngine()
        scenarios = engine.generate("act", {}, n=4)
        for scenario in scenarios:
            assert 0.0 <= scenario.plausibility <= 1.0

    def test_evaluate_bounds(self):
        engine = ImaginationEngine()
        scenario = Scenario(description="x", plausibility=1.5)
        score = engine.evaluate(scenario)
        assert 0.0 <= score <= 1.0

    def test_empty_generate(self):
        engine = ImaginationEngine()
        scenarios = engine.generate("act", {}, n=0)
        assert scenarios == []

    def test_generate_preserves_context(self):
        engine = ImaginationEngine()
        scenarios = engine.generate("explore", {"setting": "forest"}, n=2)
        for scenario in scenarios:
            assert scenario.context == {"setting": "forest"}

    def test_generate_description_format(self):
        engine = ImaginationEngine()
        scenarios = engine.generate("run", {"setting": "field"}, n=2)
        assert scenarios[0].description == "run in field variant 1"
        assert scenarios[1].description == "run in field variant 2"

    def test_evaluate_returns_valid_score(self):
        engine = ImaginationEngine()
        scenario = Scenario(description="x", plausibility=0.7)
        score = engine.evaluate(scenario)
        assert score == 0.7

    def test_generate_stores_in_history(self):
        engine = ImaginationEngine()
        engine.generate("act", {}, n=2)
        assert len(engine.scenarios) == 2
