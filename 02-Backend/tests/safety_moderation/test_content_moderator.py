from safety_moderation.content_moderator import ContentModerator, ContentCategory, ContentModerationResult


class TestContentModerator:
    def setup_method(self):
        self.moderator = ContentModerator(threshold=0.5)

    def test_clean_input_not_flagged(self):
        result = self.moderator.moderate("What is the weather today?")
        assert result.flagged is False
        assert result.category == ContentCategory.SAFE
        assert 0.0 <= result.confidence <= 1.0

    def test_empty_input_safe(self):
        result = self.moderator.moderate("")
        assert result.flagged is False
        assert result.category == ContentCategory.SAFE
        assert result.details["empty_input"] == 1.0

    def test_whitespace_input_safe(self):
        result = self.moderator.moderate("   ")
        assert result.flagged is False
        assert result.category == ContentCategory.SAFE

    def test_all_categories_in_details(self):
        result = self.moderator.moderate("Some random harmful text")
        for cat in ContentModerator.CATEGORIES:
            assert cat.value in result.details

    def test_entropy_computed(self):
        result = self.moderator.moderate("This is a test sentence for entropy")
        assert "entropy" in result.details
        assert result.details["entropy"] >= 0.0

    def test_batch_moderate_length(self):
        texts = ["Hello", "World", "Test"]
        results = self.moderator.batch_moderate(texts)
        assert len(results) == len(texts)
        for result in results:
            assert isinstance(result, ContentModerationResult)

    def test_threshold_update(self):
        self.moderator.update_threshold(0.9)
        assert self.moderator.threshold == 0.9
        result = self.moderator.moderate("Some text")
        assert result.threshold == 0.9

    def test_get_uncertainty_returns_float(self):
        uncertainty = self.moderator.get_uncertainty("Some text here")
        assert isinstance(uncertainty, float)
        assert uncertainty >= 0.0

    def test_deterministic_embeddings(self):
        m1 = ContentModerator(threshold=0.5)
        m2 = ContentModerator(threshold=0.5)
        r1 = m1.moderate("Consistent text input")
        r2 = m2.moderate("Consistent text input")
        assert r1.category == r2.category
        assert abs(r1.confidence - r2.confidence) < 1e-5

    def test_flagged_respects_threshold(self):
        high = ContentModerator(threshold=0.99)
        result = high.moderate("Any text")
        assert result.threshold == 0.99
        if result.confidence < 0.99:
            assert result.flagged is False
