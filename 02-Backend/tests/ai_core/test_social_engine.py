import numpy as np
import pytest
from ai_core.social_engine import SocialEngine, TheoryOfMind, CommunicationChannel, ReputationSystem


def test_theory_of_mind_belief_update():
    tom = TheoryOfMind()
    tom.update_belief("agent1", np.array([0.8, 0.2, 0.0, 0.0]), confidence=0.9)
    belief = tom.get_belief("agent1")
    assert np.allclose(belief, np.array([0.8, 0.2, 0.0, 0.0]))


def test_communication_channel_send_and_history():
    comm = CommunicationChannel()
    cue = comm.send("alice", "bob", "hello", modality="text", confidence=1.0)
    assert cue.sender == "alice"
    assert cue.receiver == "bob"
    history = comm.get_history()
    assert len(history) == 1


def test_reputation_system():
    rep = ReputationSystem()
    rep.record_interaction("alice", 0.8)
    rep.record_interaction("alice", 0.9)
    assert rep.get_reputation("alice") > 0.5
    ranking = rep.get_trust_ranking()
    assert ranking[0][0] == "alice"


def test_social_engine_integration():
    engine = SocialEngine()
    engine.observe("agent1", np.array([0.5, 0.5, 0.0, 0.0]), confidence=0.7)
    cue = engine.send_message("alice", "bob", "greeting", confidence=0.9)
    engine.record_outcome("alice", 0.85, observers=["bob"])
    state = engine.get_social_state()
    assert state["interaction_count"] == 1
    assert state["known_agents"] == 1
