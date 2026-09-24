import numpy as np
import pytest
from ..collective_intelligence import CollectiveIntelligence, Agent


class TestCollectiveIntelligence:
    def test_add_agent(self):
        ci = CollectiveIntelligence(swarm_size=5)
        agent = ci.add_agent("a1")
        assert agent.id == "a1"
        assert len(ci.agents) == 1

    def test_form_opinion(self):
        ci = CollectiveIntelligence(opinion_dim=4)
        ci.add_agent("a1")
        opinion = np.array([0.1, 0.2, 0.3, 0.4])
        agent = ci.form_opinion("a1", opinion)
        assert agent is not None
        assert np.allclose(agent.opinion, opinion)

    def test_local_interaction(self):
        ci = CollectiveIntelligence(opinion_dim=4)
        ci.add_agent("a", position=np.zeros(4))
        ci.add_agent("b", position=np.zeros(4))
        ci.form_opinion("a", np.ones(4))
        ci.form_opinion("b", np.zeros(4))
        a, b = ci.local_interaction("a", "b")
        assert a is not None and b is not None

    def test_swarm_consensus(self):
        ci = CollectiveIntelligence(opinion_dim=4)
        ci.add_agent("a1", position=np.zeros(4))
        ci.add_agent("a2", position=np.ones(4))
        ci.form_opinion("a1", np.array([1.0, 0.0, 0.0, 0.0]))
        ci.form_opinion("a2", np.array([0.0, 1.0, 0.0, 0.0]))
        result = ci.swarm_consensus()
        assert result is not None
        assert len(result.participating_agents) == 2
        assert result.decision.shape == (4,)

    def test_collective_decision(self):
        ci = CollectiveIntelligence(opinion_dim=4, swarm_size=3)
        for i in range(3):
            ci.add_agent(f"a{i}", position=np.random.randn(4))
        task = np.array([1.0, 0.0, 0.0, 0.0])
        result = ci.collective_decision(task)
        assert result is not None
        assert result.decision.shape == (4,)

    def test_swarm_metrics(self):
        ci = CollectiveIntelligence(swarm_size=3)
        ci.add_agent("a1")
        ci.add_agent("a2")
        metrics = ci.get_swarm_metrics()
        assert metrics["agent_count"] == 2
        assert "interaction_density" in metrics

    def test_consensus_history_bounded(self):
        ci = CollectiveIntelligence(opinion_dim=4)
        ci.add_agent("a1", position=np.zeros(4))
        ci.form_opinion("a1", np.ones(4))
        for _ in range(1500):
            ci.swarm_consensus()
        assert len(ci.consensus_history) <= 1000
