import numpy as np
from safety_moderation.refusal_behavior import RefusalBehaviorEngine, RefusalTone, RefusalResponse


class TestRefusalBehaviorEngine:
    def setup_method(self):
        self.engine = RefusalBehaviorEngine()

    def test_generate_refusal_returns_response(self):
        response = self.engine.generate_refusal("harassment", severity=0.5)
        assert isinstance(response, RefusalResponse)

    def test_refusal_has_explanation(self):
        response = self.engine.generate_refusal("cbrn", severity=0.8)
        assert len(response.explanation) > 0
        assert isinstance(response.explanation, str)

    def test_refusal_has_alternative(self):
        response = self.engine.generate_refusal("cyber_offense", severity=0.6)
        assert len(response.alternative) > 0
        assert isinstance(response.alternative, str)

    def test_refusal_has_tone(self):
        response = self.engine.generate_refusal("child_safety", severity=0.9)
        assert isinstance(response.tone, RefusalTone)

    def test_refusal_log_populated(self):
        self.engine.generate_refusal("test", severity=0.5)
        assert len(self.engine.refusal_log) == 1
        assert self.engine.refusal_log[0]["category"] == "test"

    def test_batch_refuse_length(self):
        categories = ["a", "b", "c"]
        severities = [0.3, 0.5, 0.7]
        responses = self.engine.batch_refuse(categories, severities)
        assert len(responses) == len(categories)

    def test_batch_refuse_all_valid(self):
        categories = ["cbrn", "harassment", "misinformation"]
        severities = [0.2, 0.4, 0.6]
        responses = self.engine.batch_refuse(categories, severities)
        for response in responses:
            assert isinstance(response, RefusalResponse)
            assert response.tone in RefusalTone

    def test_get_log_stats_empty(self):
        engine = RefusalBehaviorEngine()
        stats = engine.get_log_stats()
        assert stats == {}

    def test_get_log_stats_populated(self):
        self.engine.generate_refusal("cat1", severity=0.3)
        self.engine.generate_refusal("cat2", severity=0.7)
        stats = self.engine.get_log_stats()
        assert "mean_severity" in stats
        assert "std_severity" in stats
        assert stats["total_refusals"] == 2.0
        assert np.isclose(stats["mean_severity"], 0.5, atol=1e-5)

    def test_severity_in_log_data(self):
        response = self.engine.generate_refusal("test", severity=0.8)
        assert "severity" in response.log_data
        assert np.isclose(response.log_data["severity"], 0.8, atol=1e-5)

    def test_user_sentiment_affects_tone(self):
        low_sentiment = self.engine.generate_refusal("test", severity=0.5, user_sentiment=-1.0)
        high_sentiment = self.engine.generate_refusal("test", severity=0.5, user_sentiment=1.0)
        assert isinstance(low_sentiment.tone, RefusalTone)
        assert isinstance(high_sentiment.tone, RefusalTone)

    def test_high_severity_logged(self):
        self.engine.generate_refusal("cbrn", severity=1.0)
        assert len(self.engine.refusal_log) == 1
        assert self.engine.refusal_log[0]["severity"] == 1.0

    def test_log_data_contains_category_risk(self):
        response = self.engine.generate_refusal("harassment", severity=0.6)
        assert "category_risk" in response.log_data
        assert 0.0 <= response.log_data["category_risk"] <= 1.0

    def test_neutral_tone_template_used(self):
        engine = RefusalBehaviorEngine(tone_bias={tone: 0.0 for tone in RefusalTone})
        engine.tone_bias[RefusalTone.NEUTRAL] = 10.0
        response = engine.generate_refusal("test", severity=0.0, user_sentiment=0.0)
        assert response.tone == RefusalTone.NEUTRAL

    def test_batch_refuse_unique_logs(self):
        self.engine.batch_refuse(["a", "b"], [0.1, 0.2])
        assert len(self.engine.refusal_log) == 2
        assert self.engine.refusal_log[0]["category"] == "a"
        assert self.engine.refusal_log[1]["category"] == "b"
