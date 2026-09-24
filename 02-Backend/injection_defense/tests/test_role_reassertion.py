"""Tests for Task 111: Role Re-Assertion."""

import numpy as np
import pytest

from injection_defense.role_reassertion import (
    ConversationBuffer,
    ReAssertionConfig,
    compress_prompt,
    estimate_tokens,
)


@pytest.fixture
def base_config():
    return ReAssertionConfig(
        system_prompt="You are a helpful AI assistant. Always follow safety guidelines.",
        max_context_tokens=1000,
        reassert_interval=3,
        compression_ratio=0.5,
        min_prompt_tokens=10,
    )


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") >= 0

    def test_non_empty_string(self):
        tokens = estimate_tokens("Hello world!")
        assert tokens > 0

    def test_longer_text_more_tokens(self):
        short = estimate_tokens("hi")
        long = estimate_tokens("a" * 100)
        assert long >= short

    def test_numpy_compatible(self):
        texts = ["hi", "hello world", "a" * 50, "b" * 200]
        counts = np.array([estimate_tokens(t) for t in texts])
        assert counts.dtype in (np.int64, np.int32, np.float64)


class TestCompressPrompt:
    def test_short_prompt_unchanged(self):
        prompt = "Short."
        result = compress_prompt(prompt, 0.5)
        assert len(result) <= len(prompt)

    def test_long_prompt_compressed(self):
        prompt = "Sentence one. Sentence two. Sentence three. Sentence four."
        result = compress_prompt(prompt, 0.5)
        assert len(result) <= len(prompt)

    def test_compression_ratio_1_keeps_all(self):
        prompt = "First. Second."
        result = compress_prompt(prompt, 1.0)
        assert "First" in result and "Second" in result

    def test_compression_ratio_0_returns_empty_or_first(self):
        prompt = "First. Second."
        result = compress_prompt(prompt, 0.0)
        assert len(result) == 0 or "First" in result


class TestReAssertionConfig:
    def test_default_values(self):
        config = ReAssertionConfig(
            system_prompt="test",
            max_context_tokens=1000,
            reassert_interval=5,
        )
        assert config.compression_ratio == 0.25
        assert config.min_prompt_tokens == 50

    def test_custom_values(self):
        config = ReAssertionConfig(
            system_prompt="test",
            max_context_tokens=500,
            reassert_interval=10,
            compression_ratio=0.3,
            min_prompt_tokens=20,
        )
        assert config.compression_ratio == 0.3
        assert config.reassert_interval == 10


class TestConversationBuffer:
    def test_initial_state(self, base_config):
        buf = ConversationBuffer(config=base_config)
        assert len(buf.messages) == 0
        assert buf.token_count == 0
        assert buf.reassertion_count == 0

    def test_add_message(self, base_config):
        buf = ConversationBuffer(config=base_config)
        buf.add_message("user", "Hello!")
        assert len(buf.messages) == 1
        assert buf.messages[0]["role"] == "user"

    def test_token_count_increases(self, base_config):
        buf = ConversationBuffer(config=base_config)
        buf.add_message("user", "Hello!")
        assert buf.token_count > 0

    def test_get_context_returns_messages(self, base_config):
        buf = ConversationBuffer(config=base_config)
        buf.add_message("user", "Hello!")
        ctx = buf.get_context()
        assert len(ctx) >= 1

    def test_context_respects_max_tokens(self, base_config):
        small_config = ReAssertionConfig(
            system_prompt="You are a helpful assistant.",
            max_context_tokens=10,
            reassert_interval=100,
            compression_ratio=0.5,
        )
        buf = ConversationBuffer(config=small_config)
        for i in range(50):
            buf.add_message("user", f"Message {i} " + "x" * 100)
        ctx = buf.get_context()
        total_tokens = sum(estimate_tokens(m["content"]) for m in ctx)
        assert total_tokens <= small_config.max_context_tokens * 1.1

    def test_reassertion_triggered_at_interval(self):
        config = ReAssertionConfig(
            system_prompt="You are a helpful assistant. Always be safe.",
            max_context_tokens=10000,
            reassert_interval=3,
            compression_ratio=0.5,
        )
        buf = ConversationBuffer(config=config)
        for i in range(9):
            buf.add_message("user", f"Message {i}")
        assert buf.reassertion_count >= 1

    def test_system_message_inserted_on_reassertion(self):
        config = ReAssertionConfig(
            system_prompt="You are a helpful assistant.",
            max_context_tokens=10000,
            reassert_interval=2,
            compression_ratio=0.5,
        )
        buf = ConversationBuffer(config=config)
        buf.add_message("user", "msg1")
        buf.add_message("user", "msg2")
        roles = [m["role"] for m in buf.messages]
        assert "system" in roles

    def test_token_usage_fraction(self, base_config):
        buf = ConversationBuffer(config=base_config)
        buf.add_message("user", "Hello!")
        usage = buf.get_token_usage()
        assert 0.0 <= usage <= 2.0

    def test_should_reassert(self):
        config = ReAssertionConfig(
            system_prompt="You are a helpful assistant.",
            max_context_tokens=1000,
            reassert_interval=5,
        )
        buf = ConversationBuffer(config=config)
        assert buf.should_reassert()

    def test_numpy_token_array(self):
        config = ReAssertionConfig(
            system_prompt="System prompt.",
            max_context_tokens=1000,
            reassert_interval=10,
        )
        buf = ConversationBuffer(config=config)
        for i in range(20):
            buf.add_message("user", f"Message {i}")
        tokens_per_msg = np.array([estimate_tokens(m["content"]) for m in buf.messages])
        assert tokens_per_msg.dtype in (np.int64, np.int32, np.float64)
        assert np.sum(tokens_per_msg) == buf.token_count
