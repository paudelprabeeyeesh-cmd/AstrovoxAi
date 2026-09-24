from social_intelligence.social_reasoner import (
    SocialReasoner,
    SocialContext,
    PerspectiveInsight,
)


class TestSocialContext:
    def test_default_norms_empty_list(self):
        ctx = SocialContext(actors=["a"], relationship="r", setting="s")
        assert ctx.norms == []

    def test_custom_norms(self):
        ctx = SocialContext(actors=["a"], relationship="r", setting="s", norms=["be kind"])
        assert ctx.norms == ["be kind"]


class TestPerspectiveInsight:
    def test_create_insight(self):
        insight = PerspectiveInsight(
            actor="alice",
            beliefs=["alice values honesty"],
            emotions={"valence": 0.5},
            intentions=["alice likely wants to help"],
        )
        assert insight.actor == "alice"
        assert len(insight.beliefs) == 1


class TestSocialReasoner:
    def setup_method(self):
        self.reasoner = SocialReasoner()

    def test_default_norms_present(self):
        assert "be respectful" in self.reasoner.default_norms

    def test_relationship_norms_friend(self):
        assert "support" in self.reasoner.relationship_norms["friend"]

    def test_perspective_take_returns_insight(self):
        ctx = SocialContext(actors=["bob"], relationship="friend", setting="home", norms=["loyalty"])
        insight = self.reasoner.perspective_take("bob", ctx, ["self:needs"])
        assert isinstance(insight, PerspectiveInsight)
        assert insight.actor == "bob"

    def test_perspective_take_infers_beliefs_from_self(self):
        ctx = SocialContext(actors=["bob"], relationship="friend", setting="home", norms=["loyalty"])
        insight = self.reasoner.perspective_take("bob", ctx, ["self:needs"])
        assert "bob:needs" in insight.beliefs

    def test_perspective_take_positive_emotions(self):
        ctx = SocialContext(actors=["bob"], relationship="friend", setting="home", norms=["support"])
        insight = self.reasoner.perspective_take("bob", ctx, ["self:needs"])
        assert "valence" in insight.emotions
        assert insight.emotions["valence"] >= 0.0

    def test_estimate_emotions_negative(self):
        emotions = self.reasoner._estimate_emotions("x", SocialContext(actors=["x"], relationship="stranger", setting="unknown", norms=[]), ["betray"])
        assert emotions["valence"] <= 0.0

    def test_infer_intentions_positive(self):
        intentions = self.reasoner._infer_intentions("alice", [], {"valence": 0.8})
        assert any("help" in i for i in intentions)

    def test_infer_intentions_negative(self):
        intentions = self.reasoner._infer_intentions("alice", [], {"valence": -0.8})
        assert any("defensive" in i or "withdraw" in i for i in intentions)

    def test_infer_intentions_neutral(self):
        intentions = self.reasoner._infer_intentions("alice", [], {"valence": 0.0})
        assert any("neutral" in i for i in intentions)

    def test_evaluate_norm_compliance_default(self):
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="unknown", norms=[])
        scores = self.reasoner.evaluate_norm_compliance("be honest and respectful", ctx)
        assert len(scores) == len(self.reasoner.default_norms)

    def test_evaluate_norm_compliance_scores_bounded(self):
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="unknown", norms=[])
        scores = self.reasoner.evaluate_norm_compliance("be honest", ctx)
        for score in scores.values():
            assert 0.0 <= score <= 1.0

    def test_evaluate_norm_compliance_match_raises_score(self):
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="unknown", norms=["be honest"])
        scores = self.reasoner.evaluate_norm_compliance("be honest", ctx)
        assert scores["be honest"] > 0.0

    def test_suggest_repair_returns_list(self):
        ctx = SocialContext(actors=["a"], relationship="friend", setting="home", norms=["loyalty"])
        repairs = self.reasoner.suggest_repair(ctx, "lie")
        assert isinstance(repairs, list)

    def test_suggest_repair_includes_default_norms(self):
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="unknown", norms=[])
        repairs = self.reasoner.suggest_repair(ctx, "violation")
        assert any("be respectful" in r for r in repairs)

    def test_suggest_repair_includes_apology(self):
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="unknown", norms=[])
        repairs = self.reasoner.suggest_repair(ctx, "violation")
        assert any("Apologize" in r for r in repairs)

    def test_social_sensibility_returns_float(self):
        ctx = SocialContext(actors=["a"], relationship="stranger", setting="unknown", norms=[])
        sensibility = self.reasoner.evaluate_norm_compliance("be polite", ctx)
        score = self.reasoner.social_sensibility("be honest", ["a"])
        assert isinstance(score, float)

    def test_social_sensibility_bounded(self):
        score = self.reasoner.social_sensibility("be polite", ["a"])
        assert 0.0 <= score <= 1.0

    def test_social_sensibility_known_audience(self):
        score = self.reasoner.social_sensibility("be honest", ["a", "b"])
        assert 0.0 <= score <= 1.0
