import pytest
from mental_simulation.outcome_simulator import OutcomeSimulator, Outcome


class TestOutcomeSimulator:
    def test_simulate_actions(self):
        simulator = OutcomeSimulator()
        outcomes = simulator.simulate(["run", "jump"], {"base_success_rate": 0.7})
        assert len(outcomes) == 2
        assert all(isinstance(o, Outcome) for o in outcomes)

    def test_best_outcome(self):
        simulator = OutcomeSimulator()
        best = simulator.best(["a", "b"], {"base_success_rate": 0.6})
        assert best is not None
        assert isinstance(best, Outcome)

    def test_simulate_empty_actions(self):
        simulator = OutcomeSimulator()
        outcomes = simulator.simulate([], {})
        assert outcomes == []

    def test_best_empty_actions(self):
        simulator = OutcomeSimulator()
        assert simulator.best([], {}) is None

    def test_simulate_outcome_description(self):
        simulator = OutcomeSimulator()
        outcomes = simulator.simulate(["run"], {})
        assert outcomes[0].description == "outcome_run"

    def test_simulate_side_effects(self):
        simulator = OutcomeSimulator()
        outcomes = simulator.simulate(["jump"], {})
        assert outcomes[0].side_effects == ["effect_of_jump"]

    def test_simulate_probability_clamped(self):
        simulator = OutcomeSimulator()
        outcomes = simulator.simulate(["x"], {"base_success_rate": 2.0})
        assert outcomes[0].probability <= 1.0

    def test_best_returns_highest_probability(self):
        simulator = OutcomeSimulator()
        outcomes = simulator.best(["a", "b"], {"base_success_rate": 0.9})
        assert outcomes.probability == pytest.approx(0.9 + 0.1 * len(simulator.history), abs=1e-6)

    def test_simulate_stores_in_history(self):
        simulator = OutcomeSimulator()
        simulator.simulate(["x"], {})
        assert len(simulator.outcomes) == 1
