import pytest
import numpy as np
from world_model.agent_modeling import AgentModel, Belief, Intention


class TestBelief:
    def test_update_changes_confidence(self):
        b = Belief(proposition="p1", confidence=0.2)
        b.update(0.8, "e1")
        assert b.confidence > 0.2
        assert b.confidence < 0.9

    def test_update_records_evidence(self):
        b = Belief(proposition="p1")
        b.update(0.5, "e1")
        b.update(0.7, "e2")
        assert len(b.evidence) == 2


class TestAgentModel:
    def test_set_and_get_belief(self):
        agent = AgentModel("a1")
        agent.set_belief("rain", 0.8, "weather")
        belief = agent.get_belief("rain")
        assert belief is not None
        assert belief.confidence > 0.5

    def test_add_intention_sorts_by_priority(self):
        agent = AgentModel("a1")
        agent.add_intention("jump", priority=0.3)
        agent.add_intention("run", priority=0.9)
        assert agent.select_action().action == "run"

    def test_execute_returns_result(self):
        agent = AgentModel("a1", traits={"speed": 0.9})
        agent.add_intention("move")
        result = agent.execute({"time": 0})
        assert result is not None
        assert "success" in result
        assert result["agent_id"] == "a1"

    def test_belief_distribution(self):
        agent = AgentModel("a1")
        agent.set_belief("x", 0.3)
        agent.set_belief("y", 0.7)
        dist = agent.belief_distribution()
        assert "x" in dist
        assert "y" in dist
        assert 0.0 <= dist["x"] <= 1.0
        assert 0.0 <= dist["y"] <= 1.0

    def test_select_action_none_when_empty(self):
        agent = AgentModel("a1")
        assert agent.select_action() is None

    def test_execute_none_when_no_intentions(self):
        agent = AgentModel("a1")
        assert agent.execute({}) is None
