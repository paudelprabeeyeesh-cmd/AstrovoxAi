"""Tool registry and execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Any]
    requires_permission: bool = False
    timeout: int = 30


class ToolRegistry:
    """Registry for executable tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return tool.handler(arguments)


_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _tool_registry
