
import pytest
from hypothesis import given, strategies as st, assume
from app.cost import count_tokens, count_tokens_from_counts, calculate_cost
from app.analytics import UsageTracker, CostTracker, TokenTracker


class TestPropertyBasedCost:
    @given(st.integers(min_value=1, max_value=10000))
    def test_count_tokens_positive(self, token_count):
        text = " ".join(["word"] * token_count)
        result = count_tokens(text, model="gpt-4o-mini")
        assert result > 0

    @given(st.integers(min_value=0, max_value=100000), st.integers(min_value=0, max_value=100000))
    def test_count_tokens_from_counts_properties(self, prompt_tokens, completion_tokens):
        result = count_tokens_from_counts(prompt_tokens, completion_tokens)
        assert result["prompt_tokens"] == prompt_tokens
        assert result["completion_tokens"] == completion_tokens
        assert result["total_tokens"] == prompt_tokens + completion_tokens

    @given(st.integers(min_value=1, max_value=100000), st.integers(min_value=1, max_value=100000))
    def test_calculate_cost_non_negative(self, prompt_tokens, completion_tokens):
        cost = calculate_cost("gpt-4o-mini", prompt_tokens, completion_tokens)
        assert cost >= 0.0


class TestPropertyBasedAnalytics:
    @given(st.text(min_size=1))
    def test_usage_tracker_track_returns_string(self, user_id):
        with patch("app.analytics.usage_tracker.get_db") as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            tracker = UsageTracker()
            result = tracker.track_usage(user_id, "action")
            assert isinstance(result, str)
            assert len(result) > 0

    @given(st.integers(min_value=0, max_value=100000))
    def test_cost_tracker_cost_non_negative(self, tokens):
        cost = calculate_cost("gpt-4o-mini", tokens, tokens)
        assert cost >= 0.0

    @given(st.integers(min_value=1, max_value=10000))
    def test_token_tracker_total_tokens_equals_sum(self, token_count):
        result = count_tokens_from_counts(token_count, token_count)
        assert result["total_tokens"] == 2 * token_count
