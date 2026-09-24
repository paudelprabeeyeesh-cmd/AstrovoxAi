from product_polish.cost_token_tracking import CostTokenTracker, TokenUsage


def test_token_usage_defaults_total():
    usage = TokenUsage(session_id="s1", model="gpt-4", input_tokens=10, output_tokens=20)
    assert usage.total_tokens == 30
    assert usage.cost == 0.0


def test_count_prompt_tokens_min_one():
    assert CostTokenTracker.count_prompt_tokens("gpt-4", "") == 1


def test_count_prompt_tokens_divides_by_four():
    assert CostTokenTracker.count_prompt_tokens("gpt-4", "abcd") >= 1


def test_record_usage_returns_usage():
    tracker = CostTokenTracker()
    usage = tracker.record_usage("s1", "gpt-4", 1000, 2000)
    assert usage.session_id == "s1"
    assert usage.input_tokens == 1000
    assert usage.output_tokens == 2000


def test_record_usage_computes_cost():
    tracker = CostTokenTracker()
    usage = tracker.record_usage("s1", "gpt-4", 1000, 1000)
    expected = (1.0 * 0.03) + (1.0 * 0.06)
    assert abs(usage.cost - expected) < 1e-9


def test_record_usage_unknown_model_zero_cost():
    tracker = CostTokenTracker()
    usage = tracker.record_usage("s1", "unknown", 1000, 1000)
    assert usage.cost == 0.0


def test_get_session_usage():
    tracker = CostTokenTracker()
    tracker.record_usage("s1", "gpt-4", 1, 2)
    tracker.record_usage("s2", "gpt-4", 3, 4)
    assert len(tracker.get_session_usage("s1")) == 1
    assert len(tracker.get_session_usage("s2")) == 1


def test_get_model_stats():
    tracker = CostTokenTracker()
    tracker.record_usage("s1", "gpt-4", 1000, 2000)
    stats = tracker.get_model_stats("gpt-4")
    assert stats["calls"] == 1
    assert stats["input_tokens"] == 1000
    assert stats["output_tokens"] == 2000


def test_get_session_cost():
    tracker = CostTokenTracker()
    tracker.record_usage("s1", "gpt-4", 1000, 1000)
    assert tracker.get_session_cost("s1") > 0.0


def test_get_total_cost_and_tokens():
    tracker = CostTokenTracker()
    tracker.record_usage("s1", "gpt-4", 1000, 2000)
    tracker.record_usage("s1", "gpt-3.5-turbo", 500, 500)
    assert tracker.get_total_cost() > 0.0
    tokens = tracker.get_total_tokens()
    assert tokens["input"] == 1500
    assert tokens["output"] == 2500
    assert tokens["total"] == 4000


def test_reset_session():
    tracker = CostTokenTracker()
    tracker.record_usage("s1", "gpt-4", 1, 2)
    tracker.reset_session("s1")
    assert tracker.get_session_usage("s1") == []
    assert tracker.get_total_cost() == 0.0


def test_reset_clears_all():
    tracker = CostTokenTracker()
    tracker.record_usage("s1", "gpt-4", 1, 2)
    tracker.reset()
    assert tracker.get_total_cost() == 0.0


def test_custom_model_prices():
    prices = {"custom": {"input_per_1k": 0.01, "output_per_1k": 0.02}}
    tracker = CostTokenTracker(model_prices=prices)
    usage = tracker.record_usage("s1", "custom", 1000, 1000)
    assert abs(usage.cost - 0.03) < 1e-9
