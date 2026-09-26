"""Tool registry for AI agent tools."""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import inspect


class ToolCategory(Enum):
    SEARCH = "search"
    CALCULATOR = "calculator"
    DATABASE = "database"
    API = "api"
    FILE_SYSTEM = "file_system"
    CODE_EXECUTION = "code_execution"
    CUSTOM = "custom"


@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]
    required_permissions: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None
    timeout: int = 30
    cacheable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    _tools: Dict[str, ToolDefinition] = {}
    _handlers: Dict[str, Callable] = {}

    @classmethod
    def register(cls, tool: ToolDefinition, handler: Callable) -> None:
        cls._tools[tool.name] = tool
        cls._handlers[tool.name] = handler

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        return cls._tools.get(name)

    @classmethod
    def get_handler(cls, name: str) -> Optional[Callable]:
        return cls._handlers.get(name)

    @classmethod
    def list_tools(cls) -> List[ToolDefinition]:
        return list(cls._tools.values())

    @classmethod
    def list_by_category(cls, category: ToolCategory) -> List[ToolDefinition]:
        return [t for t in cls._tools.values() if t.category == category]

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._tools.pop(name, None)
        cls._handlers.pop(name, None)
