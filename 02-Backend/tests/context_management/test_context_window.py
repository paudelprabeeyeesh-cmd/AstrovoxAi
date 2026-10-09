from context_management.context_window import ContextWindow


def test_init_defaults():
    cw = ContextWindow()
    assert cw.max_tokens == 1000
    assert cw.entries == []
    assert cw.overflow_count == 0


def test_init_invalid_max_tokens():
    for invalid in (0, -1):
        try:
            ContextWindow(max_tokens=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_add_and_window():
    cw = ContextWindow(max_tokens=5)
    entry = cw.add("hello world")
    assert entry["text"] == "hello world"
    assert entry["tokens"] == 2
    window = cw.get_window()
    assert len(window) == 1
    assert window[0]["text"] == "hello world"


def test_enforce_limit():
    cw = ContextWindow(max_tokens=2)
    cw.add("one two")
    cw.add("three four five")
    assert cw.total_tokens() <= 2
    assert cw.overflow_count > 0


def test_add_with_metadata():
    cw = ContextWindow(max_tokens=10)
    entry = cw.add("hello", metadata={"source": "test"})
    assert entry["text"] == "hello"
    assert entry["source"] == "test"


def test_total_tokens_empty():
    cw = ContextWindow()
    assert cw.total_tokens() == 0


def test_estimate_tokens_single_word():
    cw = ContextWindow()
    assert cw._estimate_tokens("hello") == 1


def test_estimate_tokens_empty():
    cw = ContextWindow()
    assert cw._estimate_tokens("") == 1


def test_get_window_returns_copy():
    cw = ContextWindow(max_tokens=10)
    cw.add("hello")
    window1 = cw.get_window()
    window1.append({"text": "extra"})
    assert len(cw.get_window()) == 1


def test_enforce_limit_exact_max_tokens():
    cw = ContextWindow(max_tokens=2)
    cw.add("one two")
    assert cw.total_tokens() == 2
    assert cw.overflow_count == 0


def test_overflow_count_increments():
    cw = ContextWindow(max_tokens=1)
    cw.add("one two")
    cw.add("three four five")
    assert cw.overflow_count == 2


def test_add_empty_text():
    cw = ContextWindow(max_tokens=10)
    entry = cw.add("")
    assert entry["tokens"] == 1
    assert len(cw.entries) == 1

