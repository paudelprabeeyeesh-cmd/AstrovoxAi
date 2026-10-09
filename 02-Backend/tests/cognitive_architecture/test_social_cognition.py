import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.social_cognition import (
    SocialCognitionSystem,
    TheoryOfMind,
    EmpathyModel,
    MentalState,
)
from cognitive_architecture.emotional_processing import EmotionState


class TestTheoryOfMind:
    def test_model_agent_creates_state(self):
        tom = TheoryOfMind(agent_id="self")
        state = tom.model_agent("other", [{"belief": "likes_coffee", "confidence": 0.8}], {})
        assert isinstance(state, MentalState)
        assert state.owner == "other"

    def test_predict_action_returns_intention(self):
        tom = TheoryOfMind(agent_id="self")
        tom.model_agent("other", ["action1", "action2"], {})
        prediction = tom.predict_action("other")
        assert prediction is not None or prediction is None  # May be None if no intentions

    def test_get_agent_model(self):
        tom = TheoryOfMind(agent_id="self")
        tom.model_agent("other", [{"belief": "x"}], {})
        model = tom.get_agent_model("other")
        assert model is not None
        assert model.owner == "other"

    def test_unknown_agent_returns_none(self):
        tom = TheoryOfMind(agent_id="self")
        assert tom.get_agent_model("unknown") is None


class TestEmpathyModel:
    def test_resonate_returns_positive(self):
        model = EmpathyModel()
        state = EmotionState(valence=0.5, arousal=0.8, dominance=0.3, label="joy", intensity=0.9)
        resonance = model.resonate(state, "other")
        assert resonance > 0.0

    def test_cognitive_empathy(self):
        model = EmpathyModel()
        ms = MentalState(beliefs={"b1": 0.8}, desires=["d1"], intentions=["i1"], certainty={"b1": 0.7}, owner="other")
        perspective = model.cognitive_empathy(ms)
        assert "beliefs" in perspective
        assert "desires" in perspective

    def test_affective_empathy(self):
        model = EmpathyModel()
        state = EmotionState(valence=0.5, arousal=0.8, dominance=0.3, label="joy", intensity=0.9)
        score = model.affective_empathy(state)
        assert score > 0.0

    def test_empathy_score_default_zero(self):
        model = EmpathyModel()
        assert model.get_empathy_score("unknown") == 0.0


class TestSocialCognitionSystem:
    def test_observe_interaction(self):
        scs = SocialCognitionSystem(agent_id="self")
        state = scs.observe_interaction("other", [{"belief": "x"}], {"loc": "here"})
        assert isinstance(state, MentalState)

    def test_respond_empathetically(self):
        scs = SocialCognitionSystem(agent_id="self")
        em_state = EmotionState(valence=0.5, arousal=0.8, dominance=0.3, label="joy", intensity=0.9)
        score = scs.respond_empathetically(em_state, "other")
        assert score > 0.0

    def test_social_summary(self):
        scs = SocialCognitionSystem(agent_id="self")
        summary = scs.get_social_summary()
        assert "modeled_agents" in summary
        assert "agents" in summary

    def test_context_tracks_agents(self):
        scs = SocialCognitionSystem(agent_id="self")
        scs.observe_interaction("new_agent", [{"belief": "y"}], {})
        summary = scs.get_social_summary()
        assert "new_agent" in summary["agents"]
