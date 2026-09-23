"""
Tool selector based on task analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.tool_registry_core import ToolRegistry, ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class ToolSelection:
    tool_name: str
    confidence: float
    reasoning: str
    arguments: Dict[str, Any]


class ToolSelector:
    """Selects tools based on task requirements."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()

    def select(self, task: str, context: Optional[Dict[str, Any]] = None) -> Optional[ToolSelection]:
        tools = self.registry.list_tools()
        if not tools:
            return None
        context = context or {}
        task_lower = task.lower()
        scored: List[tuple[float, ToolDefinition]] = []
        for tool in tools:
            score = 0.0
            name_lower = tool.name.lower()
            if name_lower in task_lower:
                score += 0.8
            for keyword in name_lower.split("_"):
                if keyword in task_lower:
                    score += 0.2
            desc_lower = tool.description.lower()
            for token in task_lower.split():
                if token in desc_lower:
                    score += 0.1
            if tool.required_permissions and not context.get("user_roles"):
                score *= 0.5
            scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_tool = scored[0]
        if best_score <= 0.0:
            return None
        return ToolSelection(
            tool_name=best_tool.name,
            confidence=min(best_score, 1.0),
            reasoning=f"Selected {best_tool.name} based on task similarity",
            arguments={},
        )

    def get_available_tools(self) -> List[ToolDefinition]:
        return self.registry.list_tools()
