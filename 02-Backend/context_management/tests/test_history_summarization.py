import pytest
import numpy as np
from context_management.history_summarization import HistorySummarizer


class TestHistorySummarizer:
    def test_recent_kept_verbatim(self):
        summarizer = HistorySummarizer(recent_threshold=2)
        turns = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm fine"},
        ]
        result = summarizer.summarize(turns)
        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert "Summary" in result[0]["content"]
        assert result[1]["content"] == "How are you?"
        assert result[2]["content"] == "I'm fine"

    def test_all_recent_when_few_turns(self):
        summarizer = HistorySummarizer(recent_threshold=4)
        turns = [
            {"role": "user", "content": "A"},
            {"role": "assistant", "content": "B"},
        ]
        result = summarizer.summarize(turns)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_summary_count(self):
        summarizer = HistorySummarizer(recent_threshold=2)
        for _ in range(5):
            summarizer.summarize([
                {"role": "user", "content": "A"},
                {"role": "assistant", "content": "B"},
                {"role": "user", "content": "C"},
                {"role": "assistant", "content": "D"},
            ])
        assert summarizer.get_summary_count() == 5

    def test_invalid_recent_threshold(self):
        with pytest.raises(ValueError):
            HistorySummarizer(recent_threshold=0)

    def test_invalid_summary_max_length(self):
        with pytest.raises(ValueError):
            HistorySummarizer(recent_threshold=2, summary_max_length=0)

    def test_summary_truncates_long_text(self):
        summarizer = HistorySummarizer(recent_threshold=2, summary_max_length=20)
        long_text = " ".join(["word"] * 100)
        turns = [
            {"role": "user", "content": long_text},
            {"role": "assistant", "content": "A"},
            {"role": "user", "content": "B"},
            {"role": "assistant", "content": "C"},
        ]
        result = summarizer.summarize(turns)
        summary_content = result[0]["content"]
        assert len(summary_content) <= 20 + len("Summary: ")

    def test_numpy_summary_length_distribution(self):
        np.random.seed(0)
        summarizer = HistorySummarizer(recent_threshold=3, summary_max_length=100)
        lengths = []
        for _ in range(20):
            num_turns = int(np.random.randint(5, 20))
            turns = []
            for i in range(num_turns):
                content = " ".join(["word"] * int(np.random.randint(1, 50)))
                turns.append({"role": "user" if i % 2 == 0 else "assistant", "content": content})
            result = summarizer.summarize(turns)
            lengths.append(len(result))
        assert all(l >= 3 for l in lengths)
        assert all(l <= num_turns for l in lengths)

    def test_empty_turns(self):
        summarizer = HistorySummarizer(recent_threshold=2)
        result = summarizer.summarize([])
        assert result == []

    def test_single_turn(self):
        summarizer = HistorySummarizer(recent_threshold=2)
        result = summarizer.summarize([{"role": "user", "content": "hello"}])
        assert len(result) == 1
        assert result[0]["content"] == "hello"

    def test_numpy_summary_content_integrity(self):
        np.random.seed(7)
        summarizer = HistorySummarizer(recent_threshold=2, summary_max_length=200)
        for _ in range(10):
            num_turns = int(np.random.randint(4, 10))
            turns = []
            for i in range(num_turns):
                turns.append({"role": "user", "content": f"Message {i}"})
            result = summarizer.summarize(turns)
            assert result[-1]["content"] == f"Message {num_turns - 1}"
            assert result[-2]["content"] == f"Message {num_turns - 2}"
