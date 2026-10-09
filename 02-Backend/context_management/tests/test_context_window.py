import pytest
import numpy as np
from context_management.context_window import ContextWindow


class TestContextWindow:
    def test_invalid_max_tokens(self):
        with pytest.raises(ValueError):
            ContextWindow(max_tokens=0)

    def test_add_within_limit(self):
        window = ContextWindow(max_tokens=100)
        entry = window.add("hello world test")
        assert entry["tokens"] == 3
        assert window.total_tokens() == 3

    def test_overflow_eviction(self):
        window = ContextWindow(max_tokens=10)
        window.add("one two three four five six")
        window.add("seven eight nine ten eleven twelve")
        assert window.total_tokens() <= 10

    def test_empty_window(self):
        window = ContextWindow(max_tokens=100)
        assert window.total_tokens() == 0
        assert window.get_window() == []

    def test_clear(self):
        window = ContextWindow(max_tokens=100)
        window.add("hello world")
        window.clear()
        assert window.total_tokens() == 0
        assert window.overflow_count == 0

    def test_metadata_preserved(self):
        window = ContextWindow(max_tokens=100)
        entry = window.add("hello world", metadata={"source": "test"})
        assert entry["source"] == "test"

    def test_overflow_count(self):
        window = ContextWindow(max_tokens=5)
        window.add("one two three four five six seven")
        assert window.overflow_count >= 1

    def test_numpy_random_adds(self):
        np.random.seed(1)
        for _ in range(30):
            max_tokens = int(np.random.randint(5, 50))
            window = ContextWindow(max_tokens=max_tokens)
            for i in range(20):
                length = int(np.random.randint(1, 10))
                content = " ".join(["w"] * length)
                window.add(content)
            assert window.total_tokens() <= max_tokens

    def test_add_empty_string(self):
        window = ContextWindow(max_tokens=100)
        entry = window.add("")
        assert entry["tokens"] == 1
        assert window.total_tokens() == 1
