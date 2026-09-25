"""Regression tests — ensure previously fixed bugs stay fixed."""

import pytest


def test_chat_stream_does_not_crash_on_empty_input():
    from app.chat import ChatService
    service = ChatService()
    result = service.handle_message(user_id="test", message="", history=[])
    assert result is not None


def test_rate_limiter_allows_within_limit():
    from app.rate_limiter import RateLimiter
    limiter = RateLimiter(limit=5, window=60)
    for _ in range(5):
        assert limiter.is_allowed("user_1") is True
    assert limiter.is_allowed("user_1") is False


def test_cache_does_not_return_expired_values():
    from app.cache import InMemoryCache
    cache = InMemoryCache()
    cache.set("key", "value", ttl=0.1)
    assert cache.get("key") == "value"
    import time; time.sleep(0.15)
    assert cache.get("key") is None


def test_code_executor_rejects_dangerous_imports():
    from app.code_executor import CodeExecutor
    executor = CodeExecutor()
    result = executor.execute_python("import os; os.system('echo HACKED')")
    assert result.return_code != 0 or "HACKED" not in result.stdout


def test_search_returns_results_for_existing_query():
    from app.search import SearchEngine
    engine = SearchEngine()
    results = engine.semantic_search("test", "user_1", top_k=5)
    assert isinstance(results, list)


def test_analytics_records_event():
    from app.analytics import AnalyticsEngine
    analytics = AnalyticsEngine()
    analytics.record_event("test_event", user_id="user_1", metadata={"key": "value"})
    stats = analytics.get_user_stats("user_1")
    assert stats["total_events"] >= 1


def test_tokenizer_roundtrip():
    from app.tokenizer_data import TokenizerWrapper
    tokenizer = TokenizerWrapper()
    text = "Hello, world! This is a test."
    tokens = tokenizer.encode(text)
    decoded = tokenizer.decode(tokens)
    assert decoded == text
