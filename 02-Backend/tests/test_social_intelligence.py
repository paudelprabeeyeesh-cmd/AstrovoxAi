import pytest
import numpy as np
from agi_core.social_intelligence import SocialIntelligence


class TestSocialIntelligence:
    def test_infer_mental_state(self):
        si = SocialIntelligence()
        state = si.infer_mental_state("alice", ["positive behavior"])
        assert "valence" in state

    def test_build_relationship(self):
        si = SocialIntelligence()
        si.build_relationship("bob", "colleague")
        assert si.models["bob"].relationship == "colleague"

    def test_cooperate(self):
        si = SocialIntelligence()
        scores = si.cooperate(["alice", "bob"], "task")
        assert len(scores) == 2

    def test_negotiate(self):
        si = SocialIntelligence()
        result = si.negotiate("charlie", {"valence": 0.8, "arousal": 0.3})
        assert isinstance(result, dict)

    def test_trust_report(self):
        si = SocialIntelligence()
        si.cooperate(["x"], "t")
        report = si.get_trust_report()
        assert "mean_trust" in report
