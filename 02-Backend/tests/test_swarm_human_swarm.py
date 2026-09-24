from swarm_intelligence.human_swarm import HumanSwarmIntelligence


class TestHumanSwarmIntelligence:
    def test_predict_returns_float(self):
        swarm = HumanSwarmIntelligence(10, seed=42)
        final, estimates, conv = swarm.predict(n_rounds=5)
        assert isinstance(final, float)

    def test_convergence_decreases(self):
        swarm = HumanSwarmIntelligence(10, seed=42)
        _, _, conv = swarm.predict(n_rounds=10)
        assert len(conv) == 10
        assert conv[-1] <= conv[0] + 1e-6

    def test_estimates_length(self):
        swarm = HumanSwarmIntelligence(7, seed=42)
        _, estimates, _ = swarm.predict(n_rounds=5)
        assert len(estimates) == 7
