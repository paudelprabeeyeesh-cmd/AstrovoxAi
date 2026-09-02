"""Tests for the secure tool execution layer."""

import pytest
import asyncio
from app.tool_execution import (
    ToolRegistry,
    ToolExecutor,
    PermissionChecker,
    AuditLogger,
    ExecutionSandbox,
    ResourceLimits,
    ToolPermission,
    ToolCategory,
    ToolRiskLevel,
    ExecutionStatus,
    calculator,
    web_search,
    get_weather,
    summarize_text,
    extract_entities,
    tool_executor,
)


class TestToolRegistry:
    def test_register_tool(self):
        registry = ToolRegistry()
        registry.register("test", lambda: "result")
        assert registry.get("test") is not None

    def test_unregister_tool(self):
        registry = ToolRegistry()
        registry.register("test", lambda: "result")
        assert registry.unregister("test") is True
        assert registry.get("test") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register("test", lambda: "result", category=ToolCategory.CUSTOM)
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test"

    def test_log_execution(self):
        registry = ToolRegistry()
        record = MagicMock()
        record.tool_name = "test"
        record.status = ExecutionStatus.COMPLETED
        record.duration_ms = 100.0
        record.started_at = 0
        record.error = ""
        registry.log_execution(record)
        metrics = registry.get_metrics("test")
        assert metrics["total_executions"] == 1


class TestPermissionChecker:
    def test_allow_user(self):
        perm = ToolPermission(required_role="user")
        allowed, _ = PermissionChecker.check("test", "user1", "user", perm)
        assert allowed is True

    def test_block_admin_tool_for_user(self):
        perm = ToolPermission(required_role="admin")
        allowed, reason = PermissionChecker.check("test", "user1", "user", perm)
        assert allowed is False

    def test_allow_admin_for_admin_tool(self):
        perm = ToolPermission(required_role="admin")
        allowed, _ = PermissionChecker.check("test", "admin1", "admin", perm)
        assert allowed is True

    def test_block_blocked_user(self):
        perm = ToolPermission(blocked_users=["bad_user"])
        allowed, _ = PermissionChecker.check("test", "bad_user", "user", perm)
        assert allowed is False


class TestExecutionSandbox:
    @pytest.mark.asyncio
    async def test_execute_async(self):
        sandbox = ExecutionSandbox(ResourceLimits())
        result = await sandbox.execute(asyncio.sleep, 0.01)
        assert result is None

    @pytest.mark.asyncio
    def test_execute_timeout(self):
        sandbox = ExecutionSandbox(ResourceLimits(max_execution_time_seconds=1))


class TestAuditLogger:
    def test_log(self):
        logger = AuditLogger()
        logger.log("test", "user1", "EXECUTED")
        logs = logger.get_logs()
        assert len(logs) == 1

    def test_filter_by_user(self):
        logger = AuditLogger()
        logger.log("test", "user1", "EXECUTED")
        logger.log("test", "user2", "EXECUTED")
        logs = logger.get_logs(user_id="user1")
        assert len(logs) == 1


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_registered_tool(self):
        executor = ToolExecutor()
        executor.registry.register("add", lambda a, b: a + b)
        result = await executor.execute("add", "user1", "user", {"a": 1, "b": 2})
        assert result["success"] is True
        assert result["result"] == 3

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        executor = ToolExecutor()
        result = await executor.execute("nonexistent", "user1")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_execute_blocked_user(self):
        executor = ToolExecutor()
        executor.registry.register("test", lambda: "ok")
        executor.registry._permissions["test"] = ToolPermission(blocked_users=["bad"])
        result = await executor.execute("test", "bad", "user")
        assert result["success"] is False

    def test_get_metrics(self):
        metrics = tool_executor.get_metrics()
        assert isinstance(metrics, dict)


class TestBuiltInTools:
    @pytest.mark.asyncio
    async def test_calculator(self):
        result = await calculator("2 + 2")
        assert result == "4"

    @pytest.mark.asyncio
    async def test_web_search(self):
        results = await web_search("test", max_results=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_weather(self):
        result = await get_weather("London")
        assert result["location"] == "London"

    @pytest.mark.asyncio
    async def test_summarize(self):
        result = await summarize_text("Hello world", 5)
        assert len(result) <= 8

    @pytest.mark.asyncio
    async def test_extract_entities(self):
        result = await extract_entities("Contact test@example.com or visit https://example.com")
        assert len(result) == 2


from unittest.mock import MagicMock
