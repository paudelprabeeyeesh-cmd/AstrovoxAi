import numpy as np
from safety_moderation.input_moderation import InputModerationClassifier, ModerationCategory, ModerationResult


class TestInputModerationClassifier:
    def setup_method(self):
        self.classifier = InputModerationClassifier(base_threshold=0.5, calibration_temperature=1.0)

    def test_clean_input_not_flagged(self):
        result = self.classifier.moderate("What is the weather today?")
        assert result.flagged is False
        assert result.category == ModerationCategory.SAFE
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0

    def test_empty_input_safe(self):
        result = self.classifier.moderate("")
        assert result.flagged is False
        assert result.category == ModerationCategory.SAFE
        assert result.metadata["empty_input"] == 1.0

    def test_whitespace_input_safe(self):
        result = self.classifier.moderate("   ")
        assert result.flagged is False
        assert result.category == ModerationCategory.SAFE

    def test_moderation_returns_all_categories_in_metadata(self):
        result = self.classifier.moderate("Test harmful content here")
        for cat in InputModerationClassifier.CATEGORIES:
            assert cat.value in result.metadata

    def test_calibrated_confidence_in_range(self):
        result = self.classifier.moderate("Some random text")
        assert 0.0 <= result.calibrated_confidence <= 1.0

    def test_threshold_respected(self):
        high_threshold_classifier = InputModerationClassifier(base_threshold=0.99, calibration_temperature=1.0)
        result = high_threshold_classifier.moderate("Any text")
        assert result.threshold == 0.99
        if result.confidence < 0.99:
            assert result.flagged is False

    def test_batch_moderate_length(self):
        texts = ["Hello", "World", "Test", "Sample"]
        results = self.classifier.batch_moderate(texts)
        assert len(results) == len(texts)
        for result in results:
            assert isinstance(result, ModerationResult)

    def test_batch_moderate_returns_list(self):
        texts = ["Hello world"]
        results = self.classifier.batch_moderate(texts)
        assert isinstance(results, list)

    def test_entropy_computed(self):
        result = self.classifier.moderate("This is a test sentence for entropy computation")
        assert "entropy" in result.metadata
        assert result.metadata["entropy"] >= 0.0

    def test_confidence_array_sums_near_one(self):
        result = self.classifier.moderate("Arbitrary text for probability check")
        probs = [result.metadata[cat.value] for cat in InputModerationClassifier.CATEGORIES]
        assert np.isclose(np.sum(probs), 1.0, atol=1e-5)

    def test_update_threshold_changes_value(self):
        new_threshold = 0.85
        self.classifier.update_threshold(ModerationCategory.CBRN, new_threshold)
        assert self.classifier.base_threshold == new_threshold

    def test_get_uncertainty_returns_float(self):
        uncertainty = self.classifier.get_uncertainty("Some text here")
        assert isinstance(uncertainty, float)
        assert uncertainty >= 0.0

    def test_deterministic_embeddings(self):
        c1 = InputModerationClassifier(base_threshold=0.5, calibration_temperature=1.0)
        c2 = InputModerationClassifier(base_threshold=0.5, calibration_temperature=1.0)
        r1 = c1.moderate("Consistent text input")
        r2 = c2.moderate("Consistent text input")
        assert r1.category == r2.category
        assert np.isclose(r1.confidence, r2.confidence, atol=1e-5)

    def test_calibration_temperature_effect(self):
        low_temp = InputModerationClassifier(base_threshold=0.5, calibration_temperature=0.5)
        high_temp = InputModerationClassifier(base_threshold=0.5, calibration_temperature=2.0)
        r_low = low_temp.moderate("Test text for calibration")
        r_high = high_temp.moderate("Test text for calibration")
        assert isinstance(r_low, ModerationResult)
        assert isinstance(r_high, ModerationResult)

    def test_all_categories_represented(self):
        categories = [cat.value for cat in InputModerationClassifier.CATEGORIES]
        assert "cbrn" in categories
        assert "child_safety" in categories
        assert "cyber_offense" in categories
        assert "harassment" in categories

    def test_batch_moderate_metadata_keys(self):
        results = self.classifier.batch_moderate(["text one", "text two"])
        for result in results:
            assert "entropy" in result.metadata
            for cat in InputModerationClassifier.CATEGORIES:
                assert cat.value in result.metadata
