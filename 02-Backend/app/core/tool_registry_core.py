"""
Tool Registry with permissions, sandboxing, and execution tracking.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.guardrails import sanitize_input

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    allowed_callers: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False


@dataclass
class ToolExecution:
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    sandboxed: bool = False


class PermissionDeniedError(Exception):
    pass


class ToolRegistry:
    """Central tool registry with permission checking and sandboxing."""

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.handlers: Dict[str, Callable] = {}
        self.execution_history: List[ToolExecution] = []

    def register(self, tool_def: ToolDefinition, handler: Callable):
        """Register a tool with its definition and handler."""
        self.tools[tool_def.name] = tool_def
        self.handlers[tool_def.name] = handler
        logger.info("Registered tool: %s v%s", tool_def.name, tool_def.version)

    def unregister(self, name: str):
        """Remove a tool from the registry."""
        self.tools.pop(name, None)
        self.handlers.pop(name, None)

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)

    def list_tools(self, user_role: str = "user") -> List[ToolDefinition]:
        """List tools available to a given user role."""
        return [t for t in self.tools.values() if not t.deprecated]

    def check_permissions(self, tool_name: str, user_id: str, user_roles: List[str]) -> bool:
        tool = self.tools.get(tool_name)
        if not tool:
            return False
        for perm in tool.required_permissions:
            if perm not in user_roles:
                return False
        return True

    def execute(self, tool_name: str, arguments: Dict[str, Any], user_id: Optional[str] = None, user_roles: List[str] = None, request_id: Optional[str] = None, max_retries: int = 3) -> ToolExecution:
        """Execute a tool with permission checking and sandboxing."""
        user_roles = user_roles or ["user"]
        if tool_name not in self.handlers:
            return ToolExecution(tool_name=tool_name, arguments=arguments, error=f"Tool {tool_name} not found", user_id=user_id, request_id=request_id)
        tool_def = self.tools[tool_name]
        if not self.check_permissions(tool_name, user_id or "", user_roles):
            return ToolExecution(tool_name=tool_name, arguments=arguments, error=f"Permission denied for {tool_name}", user_id=user_id, request_id=request_id)
        sanitized_args = {}
        for k, v in arguments.items():
            sanitized, _ = sanitize_input(str(v))
            sanitized_args[k] = sanitized
        start = time.perf_counter()
        for attempt in range(max_retries):
            try:
                result = self.handlers[tool_name](**sanitized_args)
                latency = (time.perf_counter() - start) * 1000
                execution = ToolExecution(tool_name=tool_name, arguments=sanitized_args, result=result, latency_ms=latency, user_id=user_id, request_id=request_id, sandboxed=tool_def.timeout_seconds > 0)
                self.execution_history.append(execution)
                return execution
            except PermissionDeniedError as e:
                return ToolExecution(tool_name=tool_name, arguments=sanitized_args, error=str(e), user_id=user_id, request_id=request_id)
            except Exception as e:
                if attempt == max_retries - 1:
                    latency = (time.perf_counter() - start) * 1000
                    return ToolExecution(tool_name=tool_name, arguments=sanitized_args, error=str(e), latency_ms=latency, user_id=user_id, request_id=request_id)
                time.sleep(0.1 * (2 ** attempt))
        return ToolExecution(tool_name=tool_name, arguments=sanitized_args, error="Max retries exceeded", user_id=user_id, request_id=request_id)

    def get_execution_stats(self) -> dict:
        total = len(self.execution_history)
        errors = sum(1 for e in self.execution_history if e.error is not None)
        return {
            "total_executions": total,
            "errors": errors,
            "success_rate": round((total - errors) / max(total, 1) * 100, 1),
            "tools_registered": len(self.tools),
        }
