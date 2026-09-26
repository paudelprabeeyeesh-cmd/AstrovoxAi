"""
Graph of Thoughts for complex reasoning and problem solving.
"""

from __future__ import annotations

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ThoughtNode:
    def __init__(self, thought: str, score: float = 0.0, parent: Optional['ThoughtNode'] = None, children: Optional[List['ThoughtNode']] = None):
        self.thought = thought
        self.score = score
        self.parent = parent
        self.children = children or []
        self.visited = False

    def add_child(self, child: 'ThoughtNode') -> None:
        self.children.append(child)
        child.parent = self


class GraphOfThoughts:
    def __init__(self, max_depth: int = 5, branching_factor: int = 3, score_fn: Optional[callable] = None):
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.score_fn = score_fn or (lambda x: len(x.split()))
        self.root: Optional[ThoughtNode] = None

    def build_graph(self, initial_thought: str, generate_fn: callable) -> ThoughtNode:
        self.root = ThoughtNode(initial_thought, score=self.score_fn(initial_thought))
        self._expand(self.root, generate_fn, 0)
        return self.root

    def _expand(self, node: ThoughtNode, generate_fn: callable, depth: int) -> None:
        if depth >= self.max_depth:
            return
        thoughts = generate_fn(node.thought, self.branching_factor)
        for thought in thoughts:
            child = ThoughtNode(thought, score=self.score_fn(thought), parent=node)
            node.add_child(child)
            self._expand(child, generate_fn, depth + 1)

    def best_path(self) -> List[str]:
        if self.root is None:
            return []
        path = []
        current = self.root
        while current is not None:
            path.append(current.thought)
            if not current.children:
                break
            current = max(current.children, key=lambda n: n.score)
        return path

    def aggregate_thoughts(self) -> str:
        if self.root is None:
            return ""
        all_thoughts = self._collect_thoughts(self.root)
        return "\n\n".join(all_thoughts)

    def _collect_thoughts(self, node: ThoughtNode) -> List[str]:
        thoughts = [node.thought]
        for child in node.children:
            thoughts.extend(self._collect_thoughts(child))
        return thoughts
