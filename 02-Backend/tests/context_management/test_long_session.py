from context_management.long_session import LongSessionManager, ToolCall, SubAgentTask


def test_init_defaults():
    mgr = LongSessionManager()
    assert mgr.max_tool_calls == 50
    assert mgr.eviction_threshold == 40


def test_init_invalid_max_tool_calls():
    for invalid in (0, -1):
        try:
            LongSessionManager(max_tool_calls=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_init_invalid_eviction_threshold():
    for invalid in (0, 51):
        try:
            LongSessionManager(max_tool_calls=50, eviction_threshold=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_add_tool_call_no_eviction():
    mgr = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
    tc = ToolCall(id="t1", name="search", tokens=10)
    result = mgr.add_tool_call(tc)
    assert result is None
    assert mgr.get_active_tool_count() == 1


def test_add_tool_call_triggers_eviction():
    mgr = LongSessionManager(max_tool_calls=5, eviction_threshold=3)
    result = None
    for i in range(3):
        result = mgr.add_tool_call(ToolCall(id=f"t{i}", name="search", tokens=10))
    assert result is not None
    assert isinstance(result, SubAgentTask)
    assert mgr.get_sub_agent_count() == 1


def test_get_active_tool_count():
    mgr = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
    mgr.add_tool_call(ToolCall(id="t1", name="search", tokens=10))
    assert mgr.get_active_tool_count() == 1


def test_get_sub_agent_count():
    mgr = LongSessionManager(max_tool_calls=5, eviction_threshold=3)
    for i in range(4):
        mgr.add_tool_call(ToolCall(id=f"t{i}", name="search", tokens=10))
    assert mgr.get_sub_agent_count() == 1


def test_get_total_tokens():
    mgr = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
    mgr.add_tool_call(ToolCall(id="t1", name="search", tokens=10))
    mgr.add_tool_call(ToolCall(id="t2", name="search", tokens=20))
    assert mgr.get_total_tokens() == 30
