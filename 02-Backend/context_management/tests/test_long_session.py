import pytest
import numpy as np
from context_management.long_session import LongSessionManager, ToolCall, SubAgentTask


class TestLongSessionManager:
    def test_add_tool_call(self):
        manager = LongSessionManager(max_tool_calls=50)
        tc = ToolCall(id="1", name="search", tokens=10)
        manager.add_tool_call(tc)
        assert manager.get_active_tool_count() == 1

    def test_eviction_triggered(self):
        manager = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
        for i in range(45):
            tc = ToolCall(id=str(i), name="tool", tokens=10)
            manager.add_tool_call(tc)
        assert manager.get_sub_agent_count() >= 1

    def test_eviction_reduces_active_tools(self):
        manager = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
        for i in range(45):
            tc = ToolCall(id=str(i), name="tool", tokens=10)
            manager.add_tool_call(tc)
        assert manager.get_active_tool_count() < 45

    def test_invalid_max_tool_calls(self):
        with pytest.raises(ValueError):
            LongSessionManager(max_tool_calls=0)

    def test_invalid_eviction_threshold(self):
        with pytest.raises(ValueError):
            LongSessionManager(max_tool_calls=50, eviction_threshold=0)

    def test_sub_agent_task_creation(self):
        task = SubAgentTask(id="sa-1", description="test", max_tokens=500)
        task.set_context(100)
        task.set_result("done")
        assert task.context_tokens == 100
        assert task.result == "done"

    def test_sub_agent_context_exceeds_limit(self):
        task = SubAgentTask(id="sa-1", description="test", max_tokens=50)
        task.set_context(100)
        assert task.context_tokens == 50

    def test_sub_agent_negative_tokens_raises(self):
        task = SubAgentTask(id="sa-1", description="test", max_tokens=50)
        with pytest.raises(ValueError):
            task.set_context(-5)

    def test_total_tokens(self):
        manager = LongSessionManager(max_tool_calls=50)
        for i in range(10):
            tc = ToolCall(id=str(i), name="tool", tokens=5)
            manager.add_tool_call(tc)
        assert manager.get_total_tokens() == 50

    def test_numpy_large_session(self):
        np.random.seed(4)
        for _ in range(20):
            max_calls = int(np.random.randint(50, 100))
            threshold = int(np.random.randint(30, max_calls))
            manager = LongSessionManager(max_tool_calls=max_calls, eviction_threshold=threshold)
            tokens = np.random.randint(1, 20, size=max_calls).tolist()
            for i, t in enumerate(tokens):
                tc = ToolCall(id=str(i), name="tool", tokens=t)
                manager.add_tool_call(tc)
            assert manager.get_active_tool_count() <= max_calls
            assert manager.get_total_tokens() >= 0

    def test_no_eviction_under_threshold(self):
        manager = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
        for i in range(35):
            tc = ToolCall(id=str(i), name="tool", tokens=10)
            manager.add_tool_call(tc)
        assert manager.get_sub_agent_count() == 0

    def test_evicted_count(self):
        manager = LongSessionManager(max_tool_calls=50, eviction_threshold=40)
        for i in range(45):
            tc = ToolCall(id=str(i), name="tool", tokens=10)
            manager.add_tool_call(tc)
        assert manager.evicted_count > 0
