"""
Tests for product_polish.cost_token_tracking

Uses only stdlib.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest  # noqa: E402

from product_polish.cost_token_tracking import (  # noqa: E402
    CostTokenTracker,
    TokenUsage,
)


@pytest.fixture()
def tracker():
    return CostTokenTracker()


class TestCostTokenTrackerInit:
    def test_default_prices_loaded(self, tracker):
        assert "gpt-4" in tracker._model_prices
        assert "claude-3-haiku" in tracker._model_prices

    def test_initial_summary_empty(self, tracker):
        s = tracker.get_summary()
        assert s["total_cost"] == 0.0
        assert s["total_calls"] == 0

    def test_custom_prices_accepted(self):
        prices = {"my-model": {"input_per_1k": 0.5, "output_per_1k": 1.5}}
        t = CostTokenTracker(model_prices=prices)
        assert "my-model" in t._model_prices
        assert t._model_prices["my-model"]["input_per_1k"] == 0.5


class TestTokenCounting:
    def test_count_prompt_tokens_positive(self):
        n = CostTokenTracker.count_prompt_tokens("m", "Hello world test")
        assert n > 0

    def test_count_prompt_tokens_empty_returns_one(self):
        n = CostTokenTracker.count_prompt_tokens("m", "")
        assert n >= 1

    def test_count_completion_tokens_positive(self):
        n = CostTokenTracker.count_completion_tokens("m", "Response text")
        assert n > 0

    def test_count_completion_tokens_empty_returns_one(self):
        n = CostTokenTracker.count_completion_tokens("m", "")
        assert n >= 1

    def test_token_counts_deterministic(self):
        text = "hello world"
        a = CostTokenTracker.count_prompt_tokens("m", text)
        b = CostTokenTracker.count_completion_tokens("m", text)
        assert a == b

    def test_longer_text_more_tokens(self):
        s1 = "hello"
        s2 = "hello world from the universe"
        t1 = CostTokenTracker.count_prompt_tokens("m", s1)
        t2 = CostTokenTracker.count_prompt_tokens("m", s2)
        assert t2 > t1


class TestComputeCost:
    def test_cost_zero_for_unknown_model(self, tracker):
        assert tracker._compute_cost("unknown-model", 100, 100, tracker._model_prices) == 0.0

    def test_cost_positive_for_known_model(self, tracker):
        assert tracker._compute_cost("gpt-4", 100, 100, tracker._model_prices) > 0.0

    def test_cost_zero_for_zero_tokens(self, tracker):
        assert tracker._compute_cost("gpt-4", 0, 0, tracker._model_prices) == 0.0

    def test_cost_proportional_to_tokens(self, tracker):
        c1 = tracker._compute_cost("gpt-4", 100, 0, tracker._model_prices)
        c2 = tracker._compute_cost("gpt-4", 200, 0, tracker._model_prices)
        assert abs(c2 - 2 * c1) < 1e-9

    def test_cost_rounds_to_6_places(self, tracker):
        import math
        c = tracker._compute_cost("gpt-4", 1, 0, tracker._model_prices)
        assert c == math.floor(c * 1e6) / 1e6


class TestRecordUsage:
    def test_record_returns_token_usage(self, tracker):
        u = tracker.record_usage("s1", "gpt-4", 100, 50)
        assert isinstance(u, TokenUsage)
        assert u.session_id == "s1"
        assert u.model == "gpt-4"
        assert u.input_tokens == 100
        assert u.output_tokens == 50

    def test_record_sets_total_tokens(self, tracker):
        u = tracker.record_usage("s1", "gpt-4", 100, 50)
        assert u.total_tokens == 150

    def test_record_sets_cost_positive(self, tracker):
        u = tracker.record_usage("s1", "gpt-4", 100, 50)
        assert u.cost > 0.0

    def test_record_appends_to_session_history(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        usage = tracker.get_session_usage("s1")
        assert len(usage) == 1

    def test_record_multiple_calls_accumulate(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s1", "gpt-4", 50, 25)
        assert len(tracker.get_session_usage("s1")) == 2

    def test_record_unknown_model_zero_cost(self, tracker):
        u = tracker.record_usage("s1", "unknown-model", 100, 50)
        assert u.cost == 0.0

    def test_record_costs_accumulate_per_model(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s1", "gpt-3.5-turbo", 100, 50)
        g4 = tracker.get_model_stats("gpt-4")
        g3 = tracker.get_model_stats("gpt-3.5-turbo")
        assert g4["cost"] > 0.0
        assert g3["cost"] > 0.0

    def test_record_calls_count_per_model(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s1", "gpt-4", 50, 25)
        s = tracker.get_model_stats("gpt-4")
        assert s["calls"] == 2


class TestGetSessionCost:
    def test_cost_zero_no_records(self, tracker):
        assert tracker.get_session_cost("s1") == 0.0

    def test_cost_positive_after_records(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        assert tracker.get_session_cost("s1") > 0.0

    def test_cost_sums_all_calls(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s1", "gpt-4", 100, 50)
        c = tracker.get_session_cost("s1")
        assert abs(c - 2 * tracker.record_usage("s2", "gpt-4", 100, 50).cost) < 1e-6


class TestGetTotalCost:
    def test_total_zero_initially(self, tracker):
        assert tracker.get_total_cost() == 0.0

    def test_total_sums_all_models(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s1", "gpt-3.5-turbo", 100, 50)
        total = tracker.get_total_cost()
        assert abs(total - (tracker.get_model_stats("gpt-4")["cost"] + tracker.get_model_stats("gpt-3.5-turbo")["cost"])) < 1e-6


class TestGetTotalTokens:
    def test_total_tokens_zero_initially(self, tracker):
        t = tracker.get_total_tokens()
        assert t["input"] == 0
        assert t["output"] == 0
        assert t["total"] == 0

    def test_total_tokens_sums(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s2", "gpt-4", 50, 25)
        t = tracker.get_total_tokens()
        assert t["input"] == 150
        assert t["output"] == 75
        assert t["total"] == 225

    def test_total_sums_cross_session(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 0)
        tracker.record_usage("s2", "gpt-3.5-turbo", 0, 50)
        t = tracker.get_total_tokens()
        assert t["total"] == 150


class TestGetSummary:
    def test_summary_keys(self, tracker):
        s = tracker.get_summary()
        assert "total_cost" in s
        assert "total_calls" in s
        assert "tokens" in s
        assert "model_stats" in s

    def test_summary_empty_cost_zero(self, tracker):
        assert tracker.get_summary()["total_cost"] == 0.0

    def test_summary_calls_after_record(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        assert tracker.get_summary()["total_calls"] == 1


class TestReset:
    def test_reset_clears_session(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.reset_session("s1")
        assert tracker.get_session_usage("s1") == []

    def test_reset_does_not_affect_other_session(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.reset_session("s2")
        assert len(tracker.get_session_usage("s1")) == 1

    def test_reset_all(self, tracker):
        tracker.record_usage("s1", "gpt-4", 100, 50)
        tracker.record_usage("s2", "gpt-3.5-turbo", 100, 50)
        tracker.reset()
        assert tracker.get_total_cost() == 0.0
        assert tracker.get_session_usage("s1") == []


class TestThreadSafety:
    def test_concurrent_records(self, tracker):
        import threading
        errors = []

        def record_many():
            try:
                for i in range(20):
                    tracker.record_usage("s1", "gpt-4", 10, 5)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
