import sys
import importlib
from unittest.mock import MagicMock, patch

import pytest

# test_tool_sandbox.py stubs sys.modules["app"] with a plain ModuleType.
# Remove every app entry so Python can re-import the real package.
_app_modules = [name for name in sys.modules if name == "app" or name.startswith("app.")]
for _mod_name in _app_modules:
    sys.modules.pop(_mod_name, None)

from app.tool_registry import ToolRegistry


class TestToolRegistryPermissions:
    def test_register_with_metadata_creates_permissioned_tool(self):
        reg = ToolRegistry()
        reg.register_with_metadata(
            name="admin_tool",
            description="admin only",
            handler=lambda: "ok",
            required_permissions=["admin"],
        )
        assert reg.check_permission("admin_tool", ["admin"]) is True
        assert reg.check_permission("admin_tool", ["user"]) is False

    def test_register_backward_compatible(self):
        reg = ToolRegistry()

        class FakeTool:
            name = "legacy"
            description = "legacy tool"
            tags = []

        reg.register(FakeTool())
        assert reg.get("legacy") is not None

    def test_list_all_includes_metadata(self):
        reg = ToolRegistry()
        reg.register_with_metadata(
            name="tool_a",
            description="desc",
            handler=lambda: "ok",
            required_permissions=["read"],
            version="2.0.0",
        )
        tools = reg.list_all()
        assert any(t["name"] == "tool_a" for t in tools)
        assert any(t["required_permissions"] == ["read"] for t in tools)

    def test_search_ranks_by_relevance(self):
        reg = ToolRegistry()
        reg.register_with_metadata(
            name="search_web",
            description="Search the web",
            handler=lambda: "ok",
            tags=["search"],
        )
        results = reg.search("search")
        assert len(results) >= 1
        assert results[0]["name"] == "search_web"

    def test_check_permission_missing_tool(self):
        reg = ToolRegistry()
        assert reg.check_permission("missing", ["admin"]) is False


class TestToolExecutorIntegration:
    def test_execute_without_sandbox_calls_handler(self):
        from app.tool_executor import ToolExecutor

        executor = ToolExecutor()
        result = executor.execute_tool("search_web", {"query": "hello"}, "user-1")
        assert "[web search result for: hello]" == result

    def test_execute_with_sandbox_pending_approval(self):
        from app.tool_executor import ToolExecutor
        from sandboxing.tool_sandbox import ToolSandboxStatus, ToolSandboxResult
        from sandboxing.approval_store import approval_store

        class FakeSandbox:
            def execute(self, name, arguments, user_id):
                approval_store._store.clear()
                approval = approval_store.create(
                    tool_name=name,
                    arguments=arguments,
                    user_id=user_id,
                    tier="write",
                    operation=name,
                    ttl_seconds=300,
                )
                return ToolSandboxResult(
                    status=ToolSandboxStatus.PENDING_APPROVAL,
                    approval_id=approval.approval_id,
                    message="approval required",
                )

        executor = ToolExecutor(sandbox=FakeSandbox())
        result = executor.execute_tool("file_write", {"file_path": "/tmp/x", "content": "y"}, "user-1")
        assert "Approval required" in result

    def test_execute_with_circuit_breaker_open(self):
        from app.tool_executor import ToolExecutor

        class FakeCB:
            state = "closed"

            def call(self, func, *args, **kwargs):
                raise RuntimeError("open")

        executor = ToolExecutor(circuit_breaker=FakeCB())
        result = executor.execute_tool("search_web", {"query": "x"}, "user-1")
        assert "Circuit breaker open" in result


class TestFunctionCallingIntegration:
    def test_handler_uses_enhanced_executor(self):
        from app.function_calling import FunctionCallingHandler

        handler = FunctionCallingHandler()
        assert handler.executor is not None

    def test_handler_accepts_circuit_breaker(self):
        from app.function_calling import FunctionCallingHandler

        fake_cb = MagicMock()
        handler = FunctionCallingHandler(circuit_breaker=fake_cb)
        assert handler.executor._circuit_breaker is fake_cb

    def test_handler_accepts_sandbox(self):
        from app.function_calling import FunctionCallingHandler

        fake_sandbox = MagicMock()
        handler = FunctionCallingHandler(sandbox=fake_sandbox)
        assert handler.executor._sandbox is fake_sandbox


class TestSandboxedCodeTools:
    def test_code_execute_with_sandbox_blocks_dangerous(self):
        from app.tools import code_execute

        with patch("sandboxing.command_scrubbing.CommandScrubber.scan") as mock_scan:
            mock_scan.return_value = MagicMock(blocked=True, matched_rules=["os"])
            result = code_execute("import os", sandbox=MagicMock())
            assert "blocked" in result.lower() or "Error" in result

    def test_bash_execute_with_sandbox_blocks_dangerous(self):
        from app.tools import bash_execute

        fake_sandbox = MagicMock()
        fake_sandbox.scan.return_value = MagicMock(blocked=True, matched_rules=["rm -rf"])
        result = bash_execute("rm -rf /tmp", sandbox=fake_sandbox)
        assert "blocked" in result.lower() or "Error" in result
