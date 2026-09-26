"""Tool executor with sandboxing."""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import logging


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ToolExecutor:
    _handlers: Dict[str, Callable] = {}
    _timeouts: Dict[str, int] = {}
    _logger = logging.getLogger(__name__)

    @classmethod
    def register(cls, tool_name: str, handler: Callable, timeout: int = 30) -> None:
        cls._handlers[tool_name] = handler
        cls._timeouts[tool_name] = timeout

    @classmethod
    async def execute(cls, tool_name: str, parameters: Dict[str, Any], timeout: Optional[int] = None) -> ToolResult:
        handler = cls._handlers.get(tool_name)
        if not handler:
            return ToolResult(tool_name=tool_name, success=False, error=f"Tool not found: {tool_name}")
        tool_timeout = timeout or cls._timeouts.get(tool_name, 30)
        start_time = datetime.now(timezone.utc)
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(**parameters), timeout=tool_timeout)
            else:
                result = handler(**parameters)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )
        except asyncio.TimeoutError:
            return ToolResult(tool_name=tool_name, success=False, error=f"Tool timed out after {tool_timeout}s")
        except Exception as e:
            cls._logger.error(f"Tool execution error for {tool_name}: {e}")
            return ToolResult(tool_name=tool_name, success=False, error=str(e))

    @classmethod
    def execute_sync(cls, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(cls.execute(tool_name, parameters))
        except RuntimeError:
            return asyncio.run(cls.execute(tool_name, parameters))
