from context_management.sliding_window import SlidingWindow


def test_init_defaults():
    sw = SlidingWindow()
    assert sw.max_tokens == 1000
    assert sw.window == []
    assert sw.evicted_count == 0


def test_init_invalid_max_tokens():
    for invalid in (0, -1):
        try:
            SlidingWindow(max_tokens=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_add_entry():
    sw = SlidingWindow(max_tokens=100)
    entry = sw.add("hello world")
    assert entry["content"] == "hello world"
    assert entry["tokens"] == 2
    assert len(sw.get_window()) == 1


def test_add_with_metadata():
    sw = SlidingWindow(max_tokens=100)
    entry = sw.add("hello", metadata={"key": "value"})
    assert entry["key"] == "value"


def test_enforce_boundary_evicts():
    sw = SlidingWindow(max_tokens=3)
    sw.add("one two three")
    sw.add("four five six")
    assert sw.total_tokens() <= 3
    assert sw.evicted_count > 0


def test_total_tokens():
    sw = SlidingWindow(max_tokens=100)
    sw.add("one two")
    sw.add("three four five")
    assert sw.total_tokens() == 5


def test_clear():
    sw = SlidingWindow(max_tokens=100)
    sw.add("hello")
    sw.clear()
    assert sw.window == []
    assert sw.evicted_count == 0
