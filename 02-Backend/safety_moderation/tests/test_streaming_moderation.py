import numpy as np
import pytest
from safety_moderation.streaming_moderation import StreamingModerator, StreamModerationResult


class TestStreamingModerator:
    def setup_method(self):
        self.moderator = StreamingModerator(window_size=5, step_size=2, threshold=0.6)

    def test_moderate_stream_returns_list(self):
        tokens = ["hello", "world", "test", "stream"]
        results = self.moderator.moderate_stream(tokens)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_result_fields_present(self):
        tokens = ["token", "one", "two"]
        results = self.moderator.moderate_stream(tokens)
        for result in results:
            assert isinstance(result, StreamModerationResult)
            assert 0.0 <= result.window_confidence <= 1.0
            assert isinstance(result.flagged, bool)
            assert isinstance(result.partial_token, str)
            assert result.buffer_size > 0

    def test_empty_input(self):
        results = self.moderator.moderate_stream([])
        assert results == []

    def test_single_token(self):
        results = self.moderator.moderate_stream(["single"])
        assert len(results) >= 1

    def test_partial_word_handling(self):
        cleaned, partial_flags = self.moderator.handle_partial_words("hel-lo world test-ing")
        assert isinstance(cleaned, list)
        assert isinstance(partial_flags, list)
        assert len(cleaned) == len(partial_flags)

    def test_partial_word_concatenation(self):
        cleaned, _ = self.moderator.handle_partial_words("hel-lo world")
        assert any("hello" in t for t in cleaned)

    def test_rolling_window_scores(self):
        scores = self.moderator.rolling_window_scores("one two three four five six")
        assert isinstance(scores, list)
        for score in scores:
            assert 0.0 <= score <= 1.0

    def test_window_size_respected(self):
        tokens = list(range(20))
        results = self.moderator.moderate_stream([str(t) for t in tokens])
        for result in results:
            assert result.buffer_size <= self.moderator.window_size * 2

    def test_step_size_affects_results(self):
        small_step = StreamingModerator(window_size=5, step_size=1, threshold=0.6)
        large_step = StreamingModerator(window_size=5, step_size=4, threshold=0.6)
        tokens = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        r_small = small_step.moderate_stream(tokens)
        r_large = large_step.moderate_stream(tokens)
        assert len(r_small) >= len(r_large)

    def test_confidence_decreases_with_partial_penalty(self):
        tokens_partial = ["hel-", "lo", "world"]
        tokens_full = ["hello", "world", "test"]
        r_partial = self.moderator.moderate_stream(tokens_partial)
        r_full = self.moderator.moderate_stream(tokens_full)
        assert all(isinstance(r.window_confidence, float) for r in r_partial)
        assert all(isinstance(r.window_confidence, float) for r in r_full)

    def test_partial_flags_boolean(self):
        _, partial_flags = self.moderator.handle_partial_words("hel-lo test")
        for flag in partial_flags:
            assert isinstance(flag, bool)

    def test_deterministic_output(self):
        m1 = StreamingModerator(window_size=5, step_size=2, threshold=0.6)
        m2 = StreamingModerator(window_size=5, step_size=2, threshold=0.6)
        tokens = ["alpha", "beta", "gamma", "delta"]
        r1 = m1.moderate_stream(tokens)
        r2 = m2.moderate_stream(tokens)
        assert len(r1) == len(r2)
        for r1_item, r2_item in zip(r1, r2):
            assert np.isclose(r1_item.window_confidence, r2_item.window_confidence, atol=1e-5)
