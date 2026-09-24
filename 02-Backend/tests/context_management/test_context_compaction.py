from context_management.context_compaction import ContextCompactor


def test_init_defaults():
    cc = ContextCompactor()
    assert cc.max_context_tokens == 4000
    assert cc.checkpoint_interval == 10
    assert cc.checkpoints == []
    assert cc.turn_count == 0


def test_init_invalid_checkpoint_interval():
    for invalid in (0, -1):
        try:
            ContextCompactor(checkpoint_interval=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_init_invalid_max_context_tokens():
    for invalid in (0, -1):
        try:
            ContextCompactor(max_context_tokens=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_add_turn_creates_checkpoint():
    cc = ContextCompactor(checkpoint_interval=2, max_context_tokens=100)
    cc.add_turn({"role": "user", "content": "hello"})
    result = cc.add_turn({"role": "assistant", "content": "hi"})
    assert result is not None
    assert result["turn"] == 2
    assert len(cc.checkpoints) == 1


def test_add_turn_no_checkpoint_before_interval():
    cc = ContextCompactor(checkpoint_interval=5, max_context_tokens=100)
    result = cc.add_turn({"role": "user", "content": "hello"})
    assert result is None
    assert cc.turn_count == 1


def test_current_context_accumulates():
    cc = ContextCompactor(checkpoint_interval=100, max_context_tokens=100)
    cc.add_turn({"role": "user", "content": "hello"})
    cc.add_turn({"role": "assistant", "content": "world"})
    assert "hello" in cc.current_context
    assert "world" in cc.current_context


def test_compact_within_interval():
    cc = ContextCompactor(checkpoint_interval=5, max_context_tokens=100)
    turns = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    result = cc.compact(turns)
    assert result == turns


def test_compact_above_interval():
    cc = ContextCompactor(checkpoint_interval=2, max_context_tokens=100)
    turns = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
    ]
    result = cc.compact(turns)
    assert len(result) == 3
    assert result[0]["role"] == "system"


def test_get_checkpoint_count():
    cc = ContextCompactor(checkpoint_interval=2, max_context_tokens=100)
    cc.add_turn({"role": "user", "content": "a"})
    cc.add_turn({"role": "assistant", "content": "b"})
    assert cc.get_checkpoint_count() == 1
