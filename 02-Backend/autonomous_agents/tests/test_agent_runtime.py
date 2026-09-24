from ..agent_runtime import AgentRuntime


class TestAgentRuntime:
    def test_spawn_creates_agent(self):
        rt = AgentRuntime()
        agent = rt.spawn({"key": "value"})
        assert agent.id.startswith("agent_")
        assert agent.memory == {"key": "value"}
        assert agent.status == "idle"

    def test_call_tool_succeeds(self):
        rt = AgentRuntime()
        agent = rt.spawn()
        result = rt.call_tool(agent.id, "echo", {"msg": "hi"})
        assert result is not None

    def test_call_tool_increments_step_count(self):
        rt = AgentRuntime()
        agent = rt.spawn()
        rt.call_tool(agent.id, "t", {})
        rt.call_tool(agent.id, "t", {})
        assert agent.step_count == 2

    def test_exhausted_after_max_steps(self):
        rt = AgentRuntime(max_steps=2)
        agent = rt.spawn()
        rt.call_tool(agent.id, "t", {})
        rt.call_tool(agent.id, "t", {})
        assert agent.status == "exhausted"

    def test_shutdown_removes_agent(self):
        rt = AgentRuntime()
        agent = rt.spawn()
        assert rt.shutdown(agent.id) is True
        assert rt.get_state(agent.id) is None

    def test_call_tool_missing_agent_raises(self):
        rt = AgentRuntime()
        try:
            rt.call_tool("missing", "t", {})
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")
