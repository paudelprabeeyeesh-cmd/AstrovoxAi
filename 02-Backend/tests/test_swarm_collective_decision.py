from swarm_intelligence.collective_decision import CollectiveDecision


class TestCollectiveDecision:
    def test_decision_returns_option(self):
        cd = CollectiveDecision(5, ["A", "B", "C"], seed=42)
        decision, history, conv = cd.decide(n_rounds=5)
        assert decision in ["A", "B", "C"]

    def test_history_length(self):
        cd = CollectiveDecision(5, ["A", "B"], seed=42)
        decision, history, conv = cd.decide(n_rounds=8)
        assert len(history) == 8

    def test_convergence_decreases(self):
        cd = CollectiveDecision(10, ["A", "B", "C"], seed=42)
        _, _, conv = cd.decide(n_rounds=10)
        assert len(conv) == 10
        assert conv[-1] <= conv[0] + 1e-6
