from context_management.sub_agent import SubAgentDelegator


def test_init_defaults():
    d = SubAgentDelegator()
    assert d.context_limit == 2000
    assert d.compression_ratio == 0.5
    assert d.delegations == []


def test_init_invalid_context_limit():
    for invalid in (0, -1):
        try:
            SubAgentDelegator(context_limit=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_init_invalid_compression_ratio():
    for invalid in (0.0, -0.1, 1.1):
        try:
            SubAgentDelegator(compression_ratio=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_delegate_within_limit():
    d = SubAgentDelegator(context_limit=100, compression_ratio=1.0)
    result = d.delegate("summarize", "hello world")
    assert result["within_limit"] is True
    assert result["original_tokens"] == 2
    assert d.get_delegation_count() == 1


def test_delegate_compresses():
    d = SubAgentDelegator(context_limit=100, compression_ratio=0.5)
    result = d.delegate("task", "one two three four five")
    assert result["compressed_tokens"] < result["original_tokens"]


def test_get_delegation_count():
    d = SubAgentDelegator()
    d.delegate("a", "context a")
    d.delegate("b", "context b")
    assert d.get_delegation_count() == 2


def test_get_compression_stats_empty():
    d = SubAgentDelegator()
    stats = d.get_compression_stats()
    assert stats["count"] == 0
    assert stats["avg_ratio"] == 0.0


def test_get_compression_stats():
    d = SubAgentDelegator(compression_ratio=0.5)
    d.delegate("a", "one two three four")
    d.delegate("b", "five six seven eight")
    stats = d.get_compression_stats()
    assert stats["count"] == 2
    assert stats["avg_original"] > 0
    assert stats["avg_compressed"] > 0
