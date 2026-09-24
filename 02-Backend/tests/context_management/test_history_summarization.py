from context_management.history_summarization import HistorySummarizer


def test_init_defaults():
    hs = HistorySummarizer()
    assert hs.recent_threshold == 4
    assert hs.summary_max_length == 500
    assert hs.summaries == []


def test_init_invalid_recent_threshold():
    for invalid in (0, -1):
        try:
            HistorySummarizer(recent_threshold=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_init_invalid_summary_max_length():
    for invalid in (0, -1):
        try:
            HistorySummarizer(summary_max_length=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_summarize_returns_recent_when_within_threshold():
    hs = HistorySummarizer(recent_threshold=2)
    turns = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    result = hs.summarize(turns)
    assert result == turns


def test_summarize_creates_summary():
    hs = HistorySummarizer(recent_threshold=2, summary_max_length=200)
    turns = [
        {"role": "user", "content": "one two three four five"},
        {"role": "assistant", "content": "six seven eight nine ten"},
        {"role": "user", "content": "recent one"},
        {"role": "assistant", "content": "recent two"},
    ]
    result = hs.summarize(turns)
    assert len(result) == 3
    assert result[0]["role"] == "system"
    assert "Summary:" in result[0]["content"]
    assert result[1]["content"] == "recent one"
    assert result[2]["content"] == "recent two"


def test_summarize_text_truncates_long_text():
    hs = HistorySummarizer()
    text = " ".join(["word"] * 100)
    result = hs._summarize_text(text, 20)
    assert len(result) <= 20


def test_summarize_text_short_text_unchanged():
    hs = HistorySummarizer()
    text = "short"
    assert hs._summarize_text(text, 100) == "short"


def test_get_summary_count():
    hs = HistorySummarizer(recent_threshold=2)
    hs.summarize([
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ])
    assert hs.get_summary_count() == 1
