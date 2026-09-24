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


def test_clear():
    cw = ContextWindow()
    cw.add("hello")
    cw.clear()
    assert cw.entries == []
    assert cw.overflow_count == 0
