import math
from typing import Any, Dict, List
from dataclasses import dataclass, field


@dataclass
class ToolMetadata:
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


class ToolSearchRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolMetadata] = {}

    def register(self, metadata: ToolMetadata) -> None:
        self.tools[metadata.name] = metadata

    def semantic_search(self, query: str, top_k: int = 5) -> List[ToolMetadata]:
        query_terms = set(query.lower().split())
        scored: List[tuple[float, ToolMetadata]] = []

        for tool in self.tools.values():
            score = self._similarity(query_terms, tool)
            scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:top_k]]

    def _similarity(self, query_terms: set, tool: ToolMetadata) -> float:
        desc_terms = set(tool.description.lower().split())
        tag_terms = set(" ".join(tool.tags).lower().split())
        all_tool_terms = desc_terms | tag_terms

        if not query_terms or not all_tool_terms:
            return 0.0

        intersection = query_terms & all_tool_terms
        union = query_terms | all_tool_terms
        return len(intersection) / math.log(len(union) + 1)
