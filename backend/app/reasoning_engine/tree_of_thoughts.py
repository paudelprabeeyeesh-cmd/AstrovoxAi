"""Tree of thoughts reasoning."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThoughtNode:
    node_id: str
    thought: str
    score: float
    children: List["ThoughtNode"] = field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TreeOfThoughts:
    def __init__(self) -> None:
        self._roots: Dict[str, ThoughtNode] = {}

    def add_root(self, task_id: str, thought: str) -> ThoughtNode:
        node = ThoughtNode(node_id=uuid.uuid4().hex, thought=thought, score=0.0)
        self._roots[task_id] = node
        return node

    def expand(self, parent_id: str, thought: str, score: float) -> ThoughtNode:
        node = ThoughtNode(node_id=uuid.uuid4().hex, thought=thought, score=score, parent_id=parent_id)
        for root in self._roots.values():
            if self._find_node(root, parent_id):
                self._find_node(root, parent_id).children.append(node)  # type: ignore
                break
        return node

    def best_path(self, task_id: str) -> List[ThoughtNode]:
        root = self._roots.get(task_id)
        if not root:
            return []

        def dfs(node: ThoughtNode) -> List[ThoughtNode]:
            if not node.children:
                return [node]
            best = max((dfs(child) for child in node.children), key=len)
            return [node] + best

        return dfs(root)

    def _find_node(self, root: ThoughtNode, node_id: str) -> Optional[ThoughtNode]:
        if root.node_id == node_id:
            return root
        for child in root.children:
            found = self._find_node(child, node_id)
            if found:
                return found
        return None


tree_of_thoughts = TreeOfThoughts()
