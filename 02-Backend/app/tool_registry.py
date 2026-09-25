import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._tags = {}

    def register(self, tool):
        self._tools[tool.name] = tool
        for tag in getattr(tool, "tags", []):
            self._tags.setdefault(tag, []).append(tool.name)

    def get(self, name: str):
        return self._tools.get(name)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        query_lower = query.lower()
        scored = []
        for name, tool in self._tools.items():
            score = 0.0
            if query_lower in name.lower():
                score += 0.5
            desc = getattr(tool, "description", "").lower()
            if query_lower in desc:
                score += 0.3
            for tag in getattr(tool, "tags", []):
                if query_lower in tag.lower():
                    score += 0.2
            if score > 0:
                scored.append((score, name, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"name": name, "score": score, "description": getattr(tool, "description", ""), "schema": tool.to_openai_schema() if hasattr(tool, "to_openai_schema") else None}
            for score, name, tool in scored[:limit]
        ]

    def list_all(self) -> list[dict]:
        return [
            {"name": name, "description": getattr(tool, "description", ""), "tags": getattr(tool, "tags", [])}
            for name, tool in self._tools.items()
        ]


tool_registry = ToolRegistry()
