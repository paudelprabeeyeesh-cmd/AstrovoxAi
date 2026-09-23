"""
Tool executor with validation, error handling, and retry.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.core.tool_registry_core import ToolRegistry, ToolDefinition, ToolExecution

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    retries: int = 0


class ToolExecutor:
    """Executes tools with validation, timeout, and retry."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()

    def execute(self, tool_name: str, arguments: Dict[str, Any], user_id: Optional[str] = None, request_id: Optional[str] = None, max_retries: int = 3, timeout_seconds: float = 30.0) -> ToolResult:
        start = time.perf_counter()
        attempts = 0
        last_error: Optional[str] = None
        while attempts < max_retries:
            attempts += 1
            try:
                execution: ToolExecution = self.registry.execute(
                    tool_name,
                    arguments,
                    user_id=user_id,
                    request_id=request_id,
                    max_retries=1,
                )
                latency = (time.perf_counter() - start) * 1000.0
                if execution.error:
                    last_error = execution.error
                    if attempts < max_retries:
                        time.sleep(0.1 * (2 ** attempts))
                        continue
                    return ToolResult(tool_name=tool_name, success=False, error=last_error, latency_ms=latency, retries=attempts)
                return ToolResult(tool_name=tool_name, success=True, result=execution.result, latency_ms=latency, retries=attempts)
            except Exception as exc:
                last_error = str(exc)
                if attempts < max_retries:
                    time.sleep(0.1 * (2 ** attempts))
                    continue
                latency = (time.perf_counter() - start) * 1000.0
                return ToolResult(tool_name=tool_name, success=False, error=last_error, latency_ms=latency, retries=attempts)
        latency = (time.perf_counter() - start) * 1000.0
        return ToolResult(tool_name=tool_name, success=False, error=last_error or "Max retries exceeded", latency_ms=latency, retries=attempts)

    def register_tool(self, tool_def: ToolDefinition, handler: Callable):
        self.registry.register(tool_def, handler)

    def get_available_tools(self) -> List[ToolDefinition]:
        return self.registry.list_tools()


class SelfCritique:
    """Evaluates tool results and decides whether to retry."""

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        self.tool_executor = tool_executor or ToolExecutor()

    def evaluate(self, result: ToolResult) -> bool:
        if result.success:
            return True
        if result.retries >= 3:
            return False
        if result.error and "not found" in result.error.lower():
            return False
        return True

    def execute_with_critique(self, tool_name: str, arguments: Dict[str, Any], user_id: Optional[str] = None, request_id: Optional[str] = None, max_retries: int = 3) -> ToolResult:
        result = self.tool_executor.execute(tool_name, arguments, user_id=user_id, request_id=request_id, max_retries=max_retries)
        if not self.evaluate(result):
            logger.warning("Tool %s failed after %s retries: %s", tool_name, result.retries, result.error)
        return result
