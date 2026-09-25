"""Tool function calling framework with parallel execution support."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolCallStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolCall:
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    timeout: int = 30
    required_permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FunctionCallingFramework:
    """Framework for LLM function calling with parallel execution."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        pass

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def to_schema(self) -> List[Dict[str, Any]]:
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return schemas

    async def execute(self, calls: List[Dict[str, Any]]) -> List[ToolCall]:
        tasks = []
        for call in calls:
            call_id = call.get("id", f"call_{len(tasks)}")
            tool_name = call.get("name")
            arguments = call.get("arguments", {})
            tool = self._tools.get(tool_name)
            if not tool:
                tasks.append(self._failed_call(call_id, tool_name, f"Tool not found: {tool_name}"))
                continue
            tasks.append(self._run_call(call_id, tool, arguments))
        return await asyncio.gather(*tasks)

    async def execute_parallel(self, calls: List[Dict[str, Any]]) -> List[ToolCall]:
        return await self.execute(calls)

    async def execute_sequential(self, calls: List[Dict[str, Any]]) -> List[ToolCall]:
        results = []
        for call in calls:
            result = await self.execute([call])
            results.extend(result)
        return results

    async def _run_call(self, call_id: str, tool: ToolDefinition, arguments: Dict[str, Any]) -> ToolCall:
        call = ToolCall(call_id=call_id, tool_name=tool.name, arguments=arguments, status=ToolCallStatus.RUNNING, started_at=datetime.now(timezone.utc))
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(tool.handler(**arguments), timeout=tool.timeout)
            else:
                result = tool.handler(**arguments)
            call.status = ToolCallStatus.COMPLETED
            call.result = result
        except asyncio.TimeoutError:
            call.status = ToolCallStatus.TIMEOUT
            call.error = f"Tool timed out after {tool.timeout}s"
        except Exception as exc:
            call.status = ToolCallStatus.FAILED
            call.error = str(exc)
        call.completed_at = datetime.now(timezone.utc)
        return call

    async def _failed_call(self, call_id: str, tool_name: str, error: str) -> ToolCall:
        return ToolCall(call_id=call_id, tool_name=tool_name, arguments={}, status=ToolCallStatus.FAILED, error=error, started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc))


_framework: Optional[FunctionCallingFramework] = None


def get_function_calling_framework() -> FunctionCallingFramework:
    global _framework
    if _framework is None:
        _framework = FunctionCallingFramework()
    return _framework
