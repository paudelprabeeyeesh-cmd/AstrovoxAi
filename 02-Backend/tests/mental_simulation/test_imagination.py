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
