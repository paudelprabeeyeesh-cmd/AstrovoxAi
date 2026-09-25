"""Comprehensive tool system tests."""

import ast
import operator
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.tools import CalculatorTool, CodeExecutionTool, ToolResult
from app.tools.registry import ToolRegistry as ClassToolRegistry, ToolDefinition, ToolCategory
from app.tools.executor import ToolExecutor, ToolResult as ExecutorResult
from app.tools.function_calling import FunctionCallingFramework, ToolCall, ToolCallStatus
from app.tools.schema_validator import SchemaValidator
from app.tools.permissions import ToolPermissionManager, ToolPermission, ToolAccessPolicy
from app.tools.sandbox import ToolSandbox, SandboxPolicy, SandboxMode
from app.secure_executor import SandboxConfig


class TestCalculatorTool:
    def setup_method(self):
        self.calc = CalculatorTool()

    def test_simple_addition(self):
        result = self.calc.calculate("2 + 2")
        assert result.success is True
        assert result.result == "4"
        assert result.tool_name == "calculator"

    def test_simple_subtraction(self):
        result = self.calc.calculate("10 - 3")
        assert result.success is True
        assert result.result == "7"

    def test_simple_multiplication(self):
        result = self.calc.calculate("4 * 5")
        assert result.success is True
        assert result.result == "20"

    def test_simple_division(self):
        result = self.calc.calculate("10 / 2")
        assert result.success is True
        assert result.result == "5.0"

    def test_floor_division(self):
        result = self.calc.calculate("7 // 2")
        assert result.success is True
        assert result.result == "3"

    def test_modulo(self):
        result = self.calc.calculate("10 % 3")
        assert result.success is True
        assert result.result == "1"

    def test_power(self):
        result = self.calc.calculate("2 ** 3")
        assert result.success is True
        assert result.result == "8"

    def test_unary_minus(self):
        result = self.calc.calculate("-5")
        assert result.success is True
        assert result.result == "-5"

    def test_unary_plus(self):
        result = self.calc.calculate("+5")
        assert result.success is True
        assert result.result == "5"

    def test_allowed_functions(self):
        result = self.calc.calculate("abs(-5)")
        assert result.success is True
        assert result.result == "5"

    def test_nested_expression(self):
        result = self.calc.calculate("(2 + 3) * 4")
        assert result.success is True
        assert result.result == "20"

    def test_float_expression(self):
        result = self.calc.calculate("3.5 * 2")
        assert result.success is True
        assert result.result == "7.0"

    def test_invalid_operator(self):
        result = self.calc.calculate("2 & 3")
        assert result.success is False
        assert "error" in result.result.lower()

    def test_invalid_function(self):
        result = self.calc.calculate("exec('import os')")
        assert result.success is False

    def test_unsupported_node(self):
        result = self.calc.calculate("x = 5")
        assert result.success is False

    def test_empty_expression(self):
        result = self.calc.calculate("")
        assert result.success is False

    def test_division_by_zero(self):
        result = self.calc.calculate("1 / 0")
        assert result.success is False


class TestCodeExecutionTool:
    def setup_method(self):
        self.tool = CodeExecutionTool()

    def test_simple_code_execution(self):
        result = self.tool.execute("x = 1 + 1\nprint(x)")
        assert result.success is True
        assert "2" in result.result

    def test_code_execution_with_principal(self):
        principal = MagicMock()
        principal.is_admin.return_value = True
        result = self.tool.execute("x = 42", principal=principal)
        assert result.success is True

    def test_code_execution_timeout(self):
        result = self.tool.execute("import time; time.sleep(10)", timeout=1)
        assert result.success is False
        assert "timed out" in result.error.lower() or "error" in result.error.lower()

    def test_code_execution_catches_exception(self):
        result = self.tool.execute("1 / 0")
        assert result.success is False
        assert result.error is not None

    def test_tool_result_metadata_default(self):
        result = ToolResult(success=True, result="ok", tool_name="test")
        assert result.metadata == {}


class TestFunctionCallingFramework:
    def setup_method(self):
        self.framework = FunctionCallingFramework()

    def test_register_and_get_tool(self):
        tool = ToolCall(
            call_id="1",
            tool_name="search",
            arguments={"query": "AI"},
            status=ToolCallStatus.COMPLETED,
            result="results",
        )
        self.framework._tools["search"] = ToolDefinition(
            name="search",
            description="Search",
            parameters={},
            handler=lambda **kw: "ok",
        )
        retrieved = self.framework.get_tool("search")
        assert retrieved is not None

    def test_get_tool_missing(self):
        assert self.framework.get_tool("nonexistent") is None

    def test_list_tools(self):
        self.framework._tools["t1"] = ToolDefinition(name="t1", description="", parameters={}, handler=lambda: None)
        tools = self.framework.list_tools()
        assert len(tools) == 1

    def test_to_schema(self):
        self.framework._tools["search"] = ToolDefinition(name="search", description="Search", parameters={"query": str}, handler=lambda: None)
        schemas = self.framework.to_schema()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"

    async def test_execute_tool(self):
        async def handler(x):
            return x * 2
        self.framework._tools["double"] = ToolDefinition(name="double", description="", parameters={}, handler=handler)
        results = await self.framework.execute([{"id": "1", "name": "double", "arguments": {"x": 5}}])
        assert len(results) == 1
        assert results[0].status == ToolCallStatus.COMPLETED

    async def test_execute_missing_tool(self):
        results = await self.framework.execute([{"id": "1", "name": "nonexistent", "arguments": {}}])
        assert results[0].status == ToolCallStatus.FAILED

    async def test_execute_parallel(self):
        results = await self.framework.execute_parallel([{"name": "nonexistent", "arguments": {}}])
        assert len(results) == 1

    async def test_execute_sequential(self):
        results = await self.framework.execute_sequential([{"name": "nonexistent", "arguments": {}}])
        assert len(results) == 1


class TestSchemaValidator:
    def setup_method(self):
        self.validator = SchemaValidator()

    def test_register_and_validate_string(self):
        self.validator.register_schema("test_schema", {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        })
        valid, data, error = self.validator.validate("test_schema", {"name": "hello"})
        assert valid is True
        assert error is None

    def test_validate_missing_required(self):
        self.validator.register_schema("test_schema", {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        })
        valid, data, error = self.validator.validate("test_schema", {})
        assert valid is False
        assert error is not None

    def test_validate_type_mismatch(self):
        self.validator.register_schema("test_schema", {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        })
        valid, data, error = self.validator.validate("test_schema", {"count": "not-a-number"})
        assert valid is False

    def test_get_schema_missing(self):
        assert self.validator.get_schema("nonexistent") is None


class TestPermissionManager:
    def setup_method(self):
        ToolPermissionManager._policies.clear()
        ToolPermissionManager._active_sessions.clear()

    def test_check_permission_no_policy(self):
        assert ToolPermissionManager.check_permission("any-tool", "user-1", "user", "10.0.0.1") is True

    def test_check_permission_allowed_roles(self):
        policy = ToolAccessPolicy(tool_name="admin-tool", allowed_roles={"admin"})
        ToolPermissionManager.register(policy)
        assert ToolPermissionManager.check_permission("admin-tool", "user-1", "admin", "10.0.0.1") is True
        assert ToolPermissionManager.check_permission("admin-tool", "user-1", "user", "10.0.0.1") is False

    def test_check_permission_allowed_users(self):
        policy = ToolAccessPolicy(tool_name="user-tool", allowed_users={"user-1"})
        ToolPermissionManager.register(policy)
        assert ToolPermissionManager.check_permission("user-tool", "user-1", "user", "10.0.0.1") is True
        assert ToolPermissionManager.check_permission("user-tool", "user-2", "user", "10.0.0.1") is False

    def test_check_permission_allowed_ips(self):
        policy = ToolAccessPolicy(tool_name="ip-tool", allowed_ips={"10.0.0.1"})
        ToolPermissionManager.register(policy)
        assert ToolPermissionManager.check_permission("ip-tool", "user-1", "user", "10.0.0.1") is True
        assert ToolPermissionManager.check_permission("ip-tool", "user-1", "user", "192.168.1.1") is False

    def test_check_concurrent_under_limit(self):
        policy = ToolAccessPolicy(tool_name="tool-1", max_concurrent=2)
        ToolPermissionManager.register(policy)
        ToolPermissionManager.increment_session("tool-1")
        assert ToolPermissionManager.check_concurrent("tool-1") is True

    def test_check_concurrent_at_limit(self):
        policy = ToolAccessPolicy(tool_name="tool-1", max_concurrent=1)
        ToolPermissionManager.register(policy)
        ToolPermissionManager.increment_session("tool-1")
        assert ToolPermissionManager.check_concurrent("tool-1") is False

    def test_increment_and_decrement_session(self):
        ToolPermissionManager.increment_session("tool-1")
        assert ToolPermissionManager._active_sessions["tool-1"] == 1
        ToolPermissionManager.decrement_session("tool-1")
        assert ToolPermissionManager._active_sessions["tool-1"] == 0

    def test_decrement_session_does_not_go_negative(self):
        ToolPermissionManager.decrement_session("tool-1")
        assert ToolPermissionManager._active_sessions.get("tool-1", 0) == 0


class TestToolSandbox:
    def setup_method(self):
        ToolSandbox._policies.clear()

    def test_register_and_get_policy(self):
        policy = SandboxPolicy(allowed_imports=["math"], blocked_imports=["os"])
        ToolSandbox.register_policy("safe-tool", policy)
        retrieved = ToolSandbox.get_policy("safe-tool")
        assert retrieved is not None
        assert "math" in retrieved.allowed_imports

    def test_get_policy_missing(self):
        assert ToolSandbox.get_policy("nonexistent") is None

    def test_validate_code_no_policy(self):
        valid, error = ToolSandbox.validate_code("any-tool", "x = 1")
        assert valid is True
        assert error is None

    def test_validate_code_blocked_import(self):
        policy = SandboxPolicy(blocked_imports=["os"])
        ToolSandbox.register_policy("test-tool", policy)
        valid, error = ToolSandbox.validate_code("test-tool", "import os")
        assert valid is False
        assert "os" in error

    def test_validate_code_allowed_import(self):
        policy = SandboxPolicy(allowed_imports=["math"])
        ToolSandbox.register_policy("test-tool", policy)
        valid, error = ToolSandbox.validate_code("test-tool", "import math")
        assert valid is True

    def test_validate_code_blocked_path(self):
        policy = SandboxPolicy(blocked_paths=["/etc"])
        ToolSandbox.register_policy("test-tool", policy)
        valid, error = ToolSandbox.validate_code("test-tool", "open('/etc/passwd')")
        assert valid is False

    def test_execute_sandboxed_success(self):
        result = ToolSandbox.execute_sandboxed("test-tool", "print(42)", {})
        assert result["success"] is True
        assert "42" in result.get("stdout", "")

    def test_execute_sandboxed_timeout(self):
        policy = SandboxPolicy(max_execution_time=1)
        ToolSandbox.register_policy("slow-tool", policy)
        result = ToolSandbox.execute_sandboxed("slow-tool", "import time; time.sleep(5)", {})
        assert result["success"] is False


class TestToolResultDataclass:
    def test_default_metadata(self):
        r = ToolResult(success=True, result="ok", tool_name="t")
        assert r.metadata == {}

    def test_custom_metadata(self):
        r = ToolResult(success=True, result="ok", tool_name="t", metadata={"key": "val"})
        assert r.metadata["key"] == "val"

    def test_executor_result_defaults(self):
        r = ExecutorResult(tool_name="t", success=True)
        assert r.metadata == {}
        assert r.execution_time_ms == 0.0

    def test_executor_result_with_error(self):
        r = ExecutorResult(tool_name="t", success=False, error="failed")
        assert r.error == "failed"
        assert r.success is False
