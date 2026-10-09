import pytest
import numpy as np
from context_management.sub_agent import SubAgentDelegator


class TestSubAgentDelegator:
    def test_delegate_within_limit(self):
        delegator = SubAgentDelegator(context_limit=100, compression_ratio=1.0)
        result = delegator.delegate("task1", "hello world this is a test")
        assert result["within_limit"] is True

    def test_delegate_compresses_large_context(self):
        delegator = SubAgentDelegator(context_limit=10, compression_ratio=0.5)
        large_context = " ".join(["word"] * 50)
        result = delegator.delegate("task1", large_context)
        assert result["compressed_tokens"] < result["original_tokens"]

    def test_delegation_count(self):
        delegator = SubAgentDelegator()
        delegator.delegate("task1", "context one")
        delegator.delegate("task2", "context two")
        assert delegator.get_delegation_count() == 2

    def test_invalid_context_limit(self):
        with pytest.raises(ValueError):
            SubAgentDelegator(context_limit=0)

    def test_invalid_compression_ratio(self):
        with pytest.raises(ValueError):
            SubAgentDelegator(compression_ratio=0.0)
        with pytest.raises(ValueError):
            SubAgentDelegator(compression_ratio=1.1)

    def test_compression_stats(self):
        delegator = SubAgentDelegator(context_limit=100, compression_ratio=0.5)
        delegator.delegate("task1", " ".join(["a"] * 20))
        delegator.delegate("task2", " ".join(["b"] * 30))
        stats = delegator.get_compression_stats()
        assert stats["count"] == 2
        assert stats["avg_original"] > 0

    def test_empty_delegation_stats(self):
        delegator = SubAgentDelegator()
        stats = delegator.get_compression_stats()
        assert stats["count"] == 0
        assert stats["avg_ratio"] == 0.0

    def test_numpy_random_delegations(self):
        np.random.seed(5)
        for _ in range(30):
            context_limit = int(np.random.randint(10, 200))
            compression_ratio = float(np.random.uniform(0.1, 1.0))
            delegator = SubAgentDelegator(context_limit=context_limit, compression_ratio=compression_ratio)
            num_tasks = int(np.random.randint(1, 10))
            for i in range(num_tasks):
                length = int(np.random.randint(5, 50))
                context = " ".join(["word"] * length)
                result = delegator.delegate(f"task-{i}", context)
                assert result["compressed_tokens"] <= result["original_tokens"]

    def test_numpy_compression_ratio_consistency(self):
        np.random.seed(6)
        delegator = SubAgentDelegator(context_limit=100, compression_ratio=0.5)
        for _ in range(20):
            length = int(np.random.randint(20, 100))
            context = " ".join(["token"] * length)
            result = delegator.delegate("task", context)
            expected = int(length * 0.5)
            actual = result["compressed_tokens"]
            assert actual <= expected + 1

    def test_delegation_result_keys(self):
        delegator = SubAgentDelegator(context_limit=100)
        result = delegator.delegate("task1", "some context here")
        assert "subtask" in result
        assert "original_tokens" in result
        assert "compressed_tokens" in result
        assert "context" in result
        assert "within_limit" in result

    def test_single_word_context(self):
        delegator = SubAgentDelegator(context_limit=10)
        result = delegator.delegate("task", "hello")
        assert result["compressed_tokens"] == 1
        assert result["within_limit"] is True
