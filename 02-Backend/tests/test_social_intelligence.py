import pytest
from social_intelligence.social_reasoner import SocialReasoner, SocialContext, PerspectiveInsight


class TestSocialReasoner:
    def test_perspective_take(self):
        reasoner = SocialReasoner()
        ctx = SocialContext(actors=["alice", "bob"], relationship="friend", setting="casual", norms=["support", "empathy"])
        insight = reasoner.perspective_take("alice", ctx, ["self:value cooperation"])
        assert insight.actor == "alice"
        assert len(insight.beliefs) > 0

    def test_emotions_positive_valence(self):
        reasoner = SocialReasoner()
        ctx = SocialContext(actors=["a"], relationship="friend", setting="casual", norms=["support"])
        insight = reasoner.perspective_take("a", ctx, ["a values support", "a values loyalty"])
        assert insight.emotions["valence"] > 0

    def test_norm_compliance_high(self):
        reasoner = SocialReasoner()
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="public", norms=["be respectful"])
        scores = reasoner.evaluate_norm_compliance("be respectful and kind", ctx)
        assert scores.get("be respectful", 0.0) > 0.3

    def test_repair_suggestions(self):
        reasoner = SocialReasoner()
        ctx = SocialContext(actors=["a"], relationship="colleague", setting="work", norms=[])
        repairs = reasoner.suggest_repair(ctx, "violation")
        assert len(repairs) > 0

    def test_social_sensibility(self):
        reasoner = SocialReasoner()
        score = reasoner.social_sensibility("please help me", ["stranger1", "stranger2"])
        assert 0.0 <= score <= 1.0
