"""Comprehensive agent system tests."""

import time
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.agent import (
    AgentState,
    AgentStep,
    AgentTask,
    ToolRegistry,
    AIAgent,
)
from app.agents.base import BaseAgent, AgentResult, Plan, Review
from app.tools.registry import ToolRegistry as ClassToolRegistry, ToolDefinition, ToolCategory
from app.tools.executor import ToolExecutor, ToolResult as ExecutorResult
from app.providers.base import AIProvider, ChatMessage, ChatResponse


class MockProvider(AIProvider):
    def __init__(self):
        self.name = "mock"

    async def chat(self, messages, model=None, system_prompt=None, max_tokens=None, **kwargs):
        return ChatResponse(content="mocked response", model=model or "test-model", provider=self.name, tokens=10)

    async def stream(self, messages, model=None, system_prompt=None, **kwargs):
        yield {"token": "mocked", "provider": self.name, "model": model or "test-model"}


class TestAgentState:
    def test_agent_state_values(self):
        assert AgentState.IDLE.value == "idle"
        assert AgentState.PLANNING.value == "planning"
        assert AgentState.EXECUTING.value == "executing"
        assert AgentState.WAITING.value == "waiting"
        assert AgentState.COMPLETED.value == "completed"
        assert AgentState.FAILED.value == "failed"


class TestAgentStep:
    def test_create_step(self):
        step = AgentStep(step_number=1, action="search", description="Search docs")
        assert step.step_number == 1
        assert step.action == "search"
        assert step.status == "pending"
        assert step.result == ""

    def test_step_completed(self):
        step = AgentStep(step_number=1, action="search", description="Search docs")
        step.status = "completed"
        step.result = "Found 5 docs"
        assert step.status == "completed"
        assert step.result == "Found 5 docs"


class TestAgentTask:
    def test_create_task(self):
        task = AgentTask(id="task-1", user_id="user-1", goal="Do something")
        assert task.id == "task-1"
        assert task.user_id == "user-1"
        assert task.goal == "Do something"
        assert task.state == AgentState.IDLE

    def test_task_with_steps(self):
        steps = [AgentStep(step_number=1, action="plan", description="Plan")]
        task = AgentTask(id="task-1", user_id="user-1", goal="Goal", steps=steps)
        assert len(task.steps) == 1


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        registry.register("search", lambda: "result", "Search tool")
        tool = registry.get("search")
        assert tool is not None
        assert tool["description"] == "Search tool"

    def test_get_missing_tool(self):
        registry = ToolRegistry()
        tool = registry.get("nonexistent")
        assert tool is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register("tool1", lambda: None, "Tool 1")
        registry.register("tool2", lambda: None, "Tool 2")
        tools = registry.list_tools()
        assert len(tools) == 2

    async def test_execute_tool(self):
        registry = ToolRegistry()
        async def my_tool(x):
            return x * 2
        registry.register("double", my_tool, "Double a number")
        result = await registry.execute("double", x=5)
        assert "10" in result

    async def test_execute_missing_tool(self):
        registry = ToolRegistry()
        result = await registry.execute("nonexistent")
        assert "not found" in result

    async def test_execute_tool_handles_exception(self):
        registry = ToolRegistry()
        def bad_tool():
            raise ValueError("Tool failed")
        registry.register("bad", bad_tool, "Bad tool")
        result = await registry.execute("bad")
        assert "Error" in result


class TestClassToolRegistry:
    def setup_method(self):
        ClassToolRegistry._tools.clear()
        ClassToolRegistry._handlers.clear()

    def test_register_and_get(self):
        tool = ToolDefinition(
            name="search",
            description="Search tool",
            category=ToolCategory.SEARCH,
            parameters={"query": str},
        )
        def handler(query):
            return f"Results for {query}"
        ClassToolRegistry.register(tool, handler)
        retrieved = ClassToolRegistry.get("search")
        assert retrieved is not None
        assert retrieved.name == "search"

    def test_list_tools(self):
        tool = ToolDefinition(name="calc", description="Calc", category=ToolCategory.CALCULATOR, parameters={})
        ClassToolRegistry.register(tool, lambda: None)
        tools = ClassToolRegistry.list_tools()
        assert len(tools) == 1

    def test_list_by_category(self):
        tool1 = ToolDefinition(name="search", description="Search", category=ToolCategory.SEARCH, parameters={})
        tool2 = ToolDefinition(name="calc", description="Calc", category=ToolCategory.CALCULATOR, parameters={})
        ClassToolRegistry.register(tool1, lambda: None)
        ClassToolRegistry.register(tool2, lambda: None)
        search_tools = ClassToolRegistry.list_by_category(ToolCategory.SEARCH)
        assert len(search_tools) == 1
        assert search_tools[0].name == "search"

    def test_unregister(self):
        tool = ToolDefinition(name="temp", description="Temp", category=ToolCategory.CUSTOM, parameters={})
        ClassToolRegistry.register(tool, lambda: None)
        assert ClassToolRegistry.get("temp") is not None
        ClassToolRegistry.unregister("temp")
        assert ClassToolRegistry.get("temp") is None


class TestToolExecutor:
    def setup_method(self):
        ToolExecutor._handlers.clear()
        ToolExecutor._timeouts.clear()

    async def test_execute_tool_success(self):
        def handler(x):
            return x * 2
        ToolExecutor.register("double", handler, timeout=5)
        result = await ToolExecutor.execute("double", {"x": 5})
        assert result.success is True
        assert result.tool_name == "double"

    async def test_execute_missing_tool(self):
        result = await ToolExecutor.execute("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error

    async def test_execute_async_handler(self):
        async def async_handler(x):
            return x + 1
        ToolExecutor.register("incr", async_handler, timeout=5)
        result = await ToolExecutor.execute("incr", {"x": 10})
        assert result.success is True

    async def test_execute_timeout(self):
        async def slow_handler():
            import asyncio
            await asyncio.sleep(5)
        ToolExecutor.register("slow", slow_handler, timeout=1)
        result = await ToolExecutor.execute("slow", {})
        assert result.success is False
        assert "timed out" in result.error.lower() or "error" in result.error.lower()

    async def test_execute_exception_handling(self):
        def failing_handler():
            raise RuntimeError("handler error")
        ToolExecutor.register("fail", failing_handler, timeout=5)
        result = await ToolExecutor.execute("fail", {})
        assert result.success is False
        assert "handler error" in result.error

    def test_execute_sync(self):
        def handler(x):
            return x * 3
        ToolExecutor.register("triple", handler, timeout=5)
        result = ToolExecutor.execute_sync("triple", {"x": 4})
        assert result.success is True


class TestAIAgent:
    def test_create_agent(self):
        agent = AIAgent(user_id="user-1")
        assert agent.user_id == "user-1"
        assert agent.provider is None
        assert len(agent.tools.list_tools()) > 0

    def test_create_agent_with_provider(self):
        provider = MockProvider()
        agent = AIAgent(user_id="user-1", provider=provider)
        assert agent.provider is provider

    def test_register_default_tools(self):
        agent = AIAgent(user_id="user-1")
        tool_names = [t["name"] for t in agent.tools.list_tools()]
        assert "search_memory" in tool_names
        assert "save_memory" in tool_names
        assert "calculate" in tool_names
        assert "get_time" in tool_names

    def test_tool_calculate(self):
        agent = AIAgent(user_id="user-1")
        result = agent.tools.execute("calculate", expression="2 + 2")
        assert "4" in result

    def test_tool_calculate_invalid_expression(self):
        agent = AIAgent(user_id="user-1")
        result = agent.tools.execute("calculate", expression="import os")
        assert "error" in result.lower() or "unsupported" in result.lower()

    def test_tool_get_time(self):
        agent = AIAgent(user_id="user-1")
        result = agent.tools.execute("get_time")
        assert len(result) > 0
        assert "-" in result or ":" in result

    async def test_tool_save_memory(self):
        agent = AIAgent(user_id="user-1")
        with patch("app.agent.memory_manager.save_memory", new_callable=AsyncMock) as mock_save:
            result = await agent.tools.execute("save_memory", content="test memory")
            assert "saved" in result.lower() or "success" in result.lower()

    def test_tool_summarize_short_text(self):
        agent = AIAgent(user_id="user-1")
        result = agent.tools.execute("summarize", text="Short text")
        assert result == "Short text"

    def test_tool_summarize_long_text(self):
        agent = AIAgent(user_id="user-1")
        long_text = "x" * 500
        result = agent.tools.execute("summarize", text=long_text)
        assert "..." in result

    async def test_create_task(self):
        agent = AIAgent(user_id="user-1", provider=MockProvider())
        task = await agent.create_task("Search for AI papers")
        assert task.state == AgentState.EXECUTING
        assert len(task.steps) > 0

    async def test_execute_task(self):
        agent = AIAgent(user_id="user-1", provider=MockProvider())
        task = await agent.create_task("Do research")
        executed = await agent.execute_task(task.id)
        assert executed.state in (AgentState.COMPLETED, AgentState.FAILED)

    async def test_execute_task_not_found(self):
        agent = AIAgent(user_id="user-1", provider=MockProvider())
        with pytest.raises(ValueError):
            await agent.execute_task("nonexistent-task")

    def test_get_provider_no_provider_configured(self):
        agent = AIAgent(user_id="user-1")
        with patch("app.agent.ProviderFactory.list_configured", return_value=[]):
            with pytest.raises(RuntimeError):
                agent._get_provider()


class TestBaseAgent:
    def test_base_agent_is_abstract(self):
        with pytest.raises(TypeError):
            BaseAgent("test")

    def test_concrete_agent_implementation(self):
        class ConcreteAgent(BaseAgent):
            def execute(self, task, context=None):
                return AgentResult(success=True, output="done")

            def plan(self, task):
                return Plan(steps=["step1"])

            def review(self, output):
                return Review(approved=True, feedback="good")

        agent = ConcreteAgent("concrete")
        assert agent.name == "concrete"
        result = agent.execute("task")
        assert result.success is True
        plan = agent.plan("task")
        assert len(plan.steps) == 1
        review = agent.review("output")
        assert review.approved is True


class TestAgentResult:
    def test_success_result(self):
        r = AgentResult(success=True, output="done", metadata={"tokens": 10})
        assert r.success is True
        assert r.output == "done"
        assert r.error is None
        assert r.metadata["tokens"] == 10

    def test_failure_result(self):
        r = AgentResult(success=False, output="", error="Something went wrong")
        assert r.success is False
        assert r.error == "Something went wrong"


class TestPlan:
    def test_create_plan(self):
        plan = Plan(steps=["step1", "step2", "step3"], estimated_tokens=100)
        assert len(plan.steps) == 3
        assert plan.estimated_tokens == 100

    def test_empty_plan(self):
        plan = Plan(steps=[])
        assert len(plan.steps) == 0


class TestReview:
    def test_approved_review(self):
        review = Review(approved=True, feedback="Good work", score=0.9, suggestions=["Add tests"])
        assert review.approved is True
        assert review.score == 0.9
        assert len(review.suggestions) == 1

    def test_rejected_review(self):
        review = Review(approved=False, feedback="Needs improvement", score=0.3)
        assert review.approved is False
