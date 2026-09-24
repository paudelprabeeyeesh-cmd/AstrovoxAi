import logging
import time
from typing import Any, Optional

from sandboxing.tool_metrics import tool_metrics

from .tools import get_builtin_tools

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self, circuit_breaker=None, sandbox=None, audit_logger=None):
        self._tools = {t.name: t.function for t in get_builtin_tools()}
        self._circuit_breaker = circuit_breaker
        self._sandbox = sandbox
        self._audit_logger = audit_logger

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        user_roles: Optional[list[str]] = None,
    ) -> str:
        user_roles = user_roles or ["user"]
        start = time.perf_counter()

        if self._sandbox is not None:
            try:
                from sandboxing.tool_sandbox import ToolSandbox, ToolSandboxStatus
                sandbox_result = self._sandbox.execute(tool_name, arguments, user_id)
                duration_ms = (time.perf_counter() - start) * 1000
                tool_metrics.record_call(tool_name, duration_ms, sandbox_result.status.value)
                if sandbox_result.status == ToolSandboxStatus.PENDING_APPROVAL:
                    tool_metrics.record_approval_pending(tool_name)
                    return (
                        f"Approval required: {sandbox_result.message} "
                        f"(approval_id={sandbox_result.approval_id})"
                    )
                if sandbox_result.status == ToolSandboxStatus.BLOCKED:
                    return f"Blocked: {sandbox_result.error}"
                if sandbox_result.status == ToolSandboxStatus.DENIED:
                    return f"Denied: {sandbox_result.error}"
                if sandbox_result.status == ToolSandboxStatus.ERROR:
                    return f"Error: {sandbox_result.error}"
                if sandbox_result.output is not None:
                    return sandbox_result.output
            except Exception as exc:  # noqa: BLE001
                logger.error("Sandbox execution failed: %s", exc)
                duration_ms = (time.perf_counter() - start) * 1000
                tool_metrics.record_call(tool_name, duration_ms, "error")
                if self._circuit_breaker is None:
                    return f"Sandbox error: {exc}"

        func = self._tools.get(tool_name)
        if not func:
            duration_ms = (time.perf_counter() - start) * 1000
            tool_metrics.record_call(tool_name, duration_ms, "error")
            return f"Error: tool '{tool_name}' not found"

        if self._circuit_breaker is not None:
            try:
                result = self._circuit_breaker.call(
                    self._run_tool, tool_name, func, arguments, user_id
                )
                duration_ms = (time.perf_counter() - start) * 1000
                tool_metrics.record_call(tool_name, duration_ms, "success")
                return result
            except Exception as exc:  # noqa: BLE001
                logger.error("Circuit breaker rejected tool %s: %s", tool_name, exc)
                duration_ms = (time.perf_counter() - start) * 1000
                tool_metrics.record_call(tool_name, duration_ms, "error")
                tool_metrics.record_circuit_breaker_rejection(tool_name)
                return f"Circuit breaker open: {exc}"

        result = self._run_tool(tool_name, func, arguments, user_id)
        duration_ms = (time.perf_counter() - start) * 1000
        tool_metrics.record_call(tool_name, duration_ms, "success")
        return result

    def _run_tool(self, tool_name: str, func, arguments: dict[str, Any], user_id: str) -> str:
        try:
            if tool_name in ("search_documents", "create_memory"):
                return func(user_id=user_id, **arguments)
            return func(**arguments)
        except Exception as _e:  # noqa: BLE001
            logger.error("Tool execution error: %s", _e)
            return f"Error executing {tool_name}: {_e}"

    def validate_arguments(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        func = self._tools.get(tool_name)
        if not func:
            return False
        import inspect
        sig = inspect.signature(func)
        required = [
            p.name for p in sig.parameters.values()
            if p.default == inspect.Parameter.empty
        ]
        return all(k in arguments for k in required)

    def get_available_tools(self, user_id: str) -> list[dict[str, Any]]:
        from .tools import get_builtin_tools
        tools = []
        for t in get_builtin_tools():
            schema = t.to_openai_schema()
            if t.name in ("search_documents", "create_memory"):
                schema["function"]["parameters"]["properties"]["user_id"] = {
                    "type": "string",
                    "description": f"User ID ({user_id})",
                }
            tools.append(schema)
        return tools
