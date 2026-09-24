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
