import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.singularity_pathways import (
    SingularityPathways,
    SingularityScenario,
)


class TestSingularityPathways:
    def test_simulate_exponential(self):
        sp = SingularityPathways(initial_capability=1.0, growth_rate=0.1)
        scenario = sp.simulate_scenario("test_exp", years=10, growth_model="exponential")
        assert isinstance(scenario, SingularityScenario)
        assert scenario.name == "test_exp"
        assert len(scenario.capability_curve) > 0
        assert scenario.capability_curve[-1] > scenario.capability_curve[0]

    def test_simulate_logistic(self):
        sp = SingularityPathways(initial_capability=1.0, growth_rate=0.1)
        scenario = sp.simulate_scenario("test_log", years=10, growth_model="logistic")
        assert len(scenario.capability_curve) > 0

    def test_risk_and_controllability(self):
        sp = SingularityPathways(initial_capability=1.0, growth_rate=0.5)
        scenario = sp.simulate_scenario("high_risk", years=20, growth_model="exponential")
        assert 0.0 <= scenario.risk_score <= 1.0
        assert 0.0 <= scenario.controllability <= 1.0

    def test_compare_scenarios_empty(self):
        sp = SingularityPathways()
        result = sp.compare_scenarios()
        assert result["scenario_count"] == 0

    def test_compare_scenarios(self):
        sp = SingularityPathways()
        sp.simulate_scenario("slow", years=5, growth_model="polynomial")
        sp.simulate_scenario("fast", years=20, growth_model="exponential")
        result = sp.compare_scenarios()
        assert result["scenario_count"] == 2
        assert "safest_scenario" in result

    def test_pathway_stats(self):
        sp = SingularityPathways()
        sp.simulate_scenario("test", years=5)
        stats = sp.get_pathway_stats()
        assert stats["scenarios_defined"] == 1
        assert stats["simulations_run"] == 1

    def test_simulate_unknown_model_defaults_exponential(self):
        sp = SingularityPathways()
        scenario = sp.simulate_scenario("default", years=5, growth_model="unknown")
        assert len(scenario.capability_curve) > 0

    def test_compare_scenarios_ranks(self):
        sp = SingularityPathways()
        sp.simulate_scenario("slow", years=5, growth_model="polynomial")
        sp.simulate_scenario("fast", years=30, growth_model="exponential")
        result = sp.compare_scenarios()
        assert result["scenario_count"] == 2
        assert "safest_scenario" in result
        assert "riskiest_scenario" in result
