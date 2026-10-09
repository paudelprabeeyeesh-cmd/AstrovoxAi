from social_intelligence.culture_adapter import (
    CultureAdapter,
    CulturalProfile,
    CulturalDimension,
)


class TestCulturalProfile:
    def test_default_values(self):
        profile = CulturalProfile(culture="test")
        assert profile.formality == 0.5
        assert profile.directness == 0.5
        assert profile.context_richness == 0.5


class TestCultureAdapter:
    def setup_method(self):
        self.adapter = CultureAdapter()

    def test_get_profile_default(self):
        profile = self.adapter.get_profile("unknown")
        assert profile.culture == "default"

    def test_register_profile(self):
        profile = CulturalProfile(culture="custom", formality=0.9, directness=0.2, context_richness=0.8)
        self.adapter.register_profile(profile)
        assert self.adapter.get_profile("custom") == profile

    def test_adapt_message_high_formality(self):
        adapted = self.adapter.adapt_message("hi there", "high_context")
        assert adapted.lower().startswith("[context:")

    def test_adapt_message_low_context_softens(self):
        adapted = self.adapter.adapt_message("Buy now!", "low_context")
        assert not adapted.endswith("!")

    def test_compare_profiles_returns_deltas(self):
        deltas = self.adapter.compare_profiles("high_context", "low_context")
        assert "formality_delta" in deltas
        assert "directness_delta" in deltas
        assert "context_delta" in deltas

    def test_compare_profiles_formality_delta_sign(self):
        deltas = self.adapter.compare_profiles("high_context", "low_context")
        assert deltas["formality_delta"] > 0.0

    def test_adapt_message_preserves_content(self):
        original = "Thank you for your time"
        adapted = self.adapter.adapt_message(original, "default")
        assert original in adapted

    def test_adapt_message_with_intent(self):
        adapted = self.adapter.adapt_message("hi", "high_context", intent="greeting")
        assert "[Context: greeting]" in adapted

    def test_get_profile_high_context(self):
        profile = self.adapter.get_profile("high_context")
        assert profile.formality == 0.7
        assert profile.directness == 0.3

    def test_register_profile_overwrites(self):
        profile = CulturalProfile(culture="custom", formality=0.9, directness=0.2, context_richness=0.8)
        self.adapter.register_profile(profile)
        self.adapter.register_profile(CulturalProfile(culture="custom", formality=0.1))
        assert self.adapter.get_profile("custom").formality == 0.1

    def test_adapt_message_low_formality_no_soften(self):
        adapted = self.adapter.adapt_message("Hello!", "high_context")
        assert adapted.endswith("!")

    def test_soften_without_exclamation(self):
        adapted = self.adapter.adapt_message("Hello", "low_context")
        assert adapted == "Hello"

    def test_cultural_profile_with_dimensions(self):
        dims = {CulturalDimension.INDIVIDUALISM: 0.8}
        profile = CulturalProfile(culture="test", dimensions=dims, formality=0.5)
        assert CulturalDimension.INDIVIDUALISM in profile.dimensions
        assert profile.dimensions[CulturalDimension.INDIVIDUALISM] == 0.8
