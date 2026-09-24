"""Tests for Task 110: Canary Tokens."""

import time

import numpy as np
import pytest

from injection_defense.canary_tokens import (
    CanaryRegistry,
    CanaryToken,
    check_canary,
    create_canary,
    embed_canary,
    get_global_registry,
)


@pytest.fixture(autouse=True)
def _reset_global_registry():
    registry = get_global_registry()
    original = dict(registry._tokens)
    yield
    registry._tokens = original


class TestCanaryToken:
    def test_token_value_non_empty(self):
        registry = CanaryRegistry()
        token = registry.generate()
        assert len(token.value) > 0

    def test_token_unique(self):
        registry = CanaryRegistry()
        t1 = registry.generate()
        t2 = registry.generate()
        assert t1 != t2

    def test_token_created_at_recent(self):
        registry = CanaryRegistry()
        token = registry.generate()
        assert time.time() - token.created_at < 2.0

    def test_token_not_expired_by_default(self):
        registry = CanaryRegistry()
        token = registry.generate()
        assert not token.is_expired()

    def test_token_expired_with_ttl(self):
        registry = CanaryRegistry()
        token = CanaryToken(value="TEST-TOKEN", expires_at=time.time() - 1.0)
        assert token.is_expired()

    def test_mark_used_sets_flag(self):
        registry = CanaryRegistry()
        token = registry.generate()
        assert not token.used
        token.mark_used()
        assert token.used


class TestCanaryRegistry:
    def test_generate_adds_to_registry(self):
        registry = CanaryRegistry()
        token = registry.generate()
        assert token.value in registry._tokens

    def test_check_detects_leak(self):
        registry = CanaryRegistry()
        token = registry.generate()
        text = f"Here is the answer. {token.value}"
        result = registry.check(text)
        assert result is not None
        assert result.value == token.value

    def test_check_no_leak(self):
        registry = CanaryRegistry()
        registry.generate()
        text = "Here is the answer without any token."
        assert registry.check(text) is None

    def test_check_expired_token_ignored(self):
        registry = CanaryRegistry()
        token = CanaryToken(value="EXPIRED-TOKEN", expires_at=time.time() - 10)
        registry._tokens["EXPIRED-TOKEN"] = token
        result = registry.check("Some text EXPIRED-TOKEN more text")
        assert result is None

    def test_revoke_removes_token(self):
        registry = CanaryRegistry()
        token = registry.generate()
        assert registry.revoke(token.value) is True
        assert token.value not in registry._tokens

    def test_revoke_missing_returns_false(self):
        registry = CanaryRegistry()
        assert registry.revoke("NONEXISTENT") is False

    def test_cleanup_expired(self):
        registry = CanaryRegistry()
        registry._tokens["old"] = CanaryToken("old", expires_at=time.time() - 5)
        registry._tokens["new"] = CanaryToken("new", expires_at=None)
        removed = registry.cleanup_expired()
        assert removed == 1
        assert "old" not in registry._tokens
        assert "new" in registry._tokens

    def test_active_count(self):
        registry = CanaryRegistry()
        registry.generate()
        registry.generate()
        registry._tokens["expired"] = CanaryToken("expired", expires_at=time.time() - 1)
        assert registry.active_count() == 2


class TestGlobalCanaryFunctions:
    def test_create_canary_returns_string(self):
        token = create_canary()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_check_canary_false_for_clean(self):
        assert check_canary("Hello, world!") is False

    def test_embed_canary_includes_token(self):
        text = "What is 2+2?"
        result = embed_canary(text)
        from injection_defense.canary_tokens import _CANARY_REGEX
        assert _CANARY_REGEX.search(result) is not None

    def test_embed_specific_token(self):
        specific = "MY-CUSTOM-CANARY-ABC-123"
        result = embed_canary("text", token=specific)
        assert specific in result


class TestCanaryNumpy:
    def test_token_length_distribution(self):
        registry = CanaryRegistry()
        lengths = np.array([len(registry.generate().value) for _ in range(20)])
        assert np.mean(lengths) > 10
        assert np.std(lengths) > 0

    def test_registry_size_numeric(self):
        registry = CanaryRegistry()
        for _ in range(10):
            registry.generate()
        size = registry.active_count()
        assert isinstance(size, int)
        assert size == 10

    def test_check_rate_on_clean_text(self):
        registry = CanaryRegistry()
        registry.generate()
        clean_texts = [f"clean message number {i}" for i in range(50)]
        leak_count = sum(1 for t in clean_texts if registry.is_leaked(t))
        assert leak_count == 0
