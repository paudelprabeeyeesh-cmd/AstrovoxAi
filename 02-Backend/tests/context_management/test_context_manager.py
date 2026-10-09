from context_management.context_manager import ContextManager


def test_init_defaults():
    cm = ContextManager()
    assert cm.max_tokens == 4000
    assert cm.turns == []
    assert cm.system_prompt is None


def test_init_invalid_max_tokens():
    for invalid in (0, -1):
        try:
            ContextManager(max_tokens=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_set_system_prompt_and_get_context():
    cm = ContextManager()
    cm.set_system_prompt("sys")
    cm.add_turn("user", "hello")
    cm.add_turn("assistant", "hi")
    ctx = cm.get_context()
    assert ctx[0] == {"role": "system", "content": "sys"}
    assert ctx[1] == {"role": "user", "content": "hello"}
    assert ctx[2] == {"role": "assistant", "content": "hi"}


def test_clear():
    cm = ContextManager()
    cm.set_system_prompt("sys")
    cm.add_turn("user", "hello")
    cm.clear()
    assert cm.turns == []
    assert cm.system_prompt == "sys"


def test_token_count():
    cm = ContextManager()
    cm.add_turn("user", "hello world")
    cm.add_turn("assistant", "foo bar baz")
    assert cm.token_count() == 5


def test_get_context_without_system_prompt():
    cm = ContextManager()
    cm.add_turn("user", "hello")
    ctx = cm.get_context()
    assert ctx == [{"role": "user", "content": "hello"}]


def test_get_context_empty():
    cm = ContextManager()
    assert cm.get_context() == []


def test_token_count_with_system_prompt():
    cm = ContextManager()
    cm.set_system_prompt("system prompt")
    cm.add_turn("user", "hello world")
    assert cm.token_count() == 3


def test_token_count_empty():
    cm = ContextManager()
    assert cm.token_count() == 0


def test_add_turn_returns_dict():
    cm = ContextManager()
    turn = cm.add_turn("user", "hello")
    assert turn == {"role": "user", "content": "hello"}
    assert turn in cm.turns


def test_truncate_within_limit():
    cm = ContextManager(max_tokens=100)
    cm.add_turn("user", "hello")
    cm.truncate()
    assert len(cm.turns) == 1


def test_truncate_no_infinite_loop():
    cm = ContextManager(max_tokens=1)
    cm.add_turn("user", "one two three")
    cm.truncate()
    assert cm.token_count() <= 1


def test_clear_empty():
    cm = ContextManager()
    cm.clear()
    assert cm.turns == []

