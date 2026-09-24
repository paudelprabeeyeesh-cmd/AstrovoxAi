from typing import Any, List, Optional, Callable, Dict
from collections import deque
import numpy as np


class ThoughtState:
    def __init__(self, content: str, score: float = 0.0, depth: int = 0, parent: Optional["ThoughtState"] = None):
        self.content = content
        self.score = score
        self.depth = depth
        self.parent = parent
        self.children: List["ThoughtState"] = []

    def __repr__(self):
        return f"ThoughtState(content={self.content!r}, score={self.score:.2f}, depth={self.depth})"


class ToTSearch:
    def __init__(
        self,
        initial_state: str,
        generate_thoughts_fn: Callable[[str, int], List[str]],
        evaluate_fn: Callable[[str], float],
        max_depth: int = 3,
        branching_factor: int = 5,
        beam_width: int = 3,
    ):
        self.initial_state = initial_state
        self.generate_thoughts_fn = generate_thoughts_fn
        self.evaluate_fn = evaluate_fn
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.beam_width = beam_width

    def bfs_search(self) -> Optional[ThoughtState]:
        root = ThoughtState(content=self.initial_state, depth=0)
        root.score = self.evaluate_fn(root.content)
        queue = deque([root])
        best_node = root

        while queue:
            current = queue.popleft()
            if current.depth >= self.max_depth:
                continue
            thoughts = self.generate_thoughts_fn(current.content, self.branching_factor)
            scored_thoughts = [(t, self.evaluate_fn(t)) for t in thoughts]
            scored_thoughts.sort(key=lambda x: x[1], reverse=True)
            top_thoughts = scored_thoughts[: self.beam_width]

            for thought, score in top_thoughts:
                child = ThoughtState(content=thought, score=score, depth=current.depth + 1, parent=current)
                current.children.append(child)
                queue.append(child)
                if score > best_node.score:
                    best_node = child

        return best_node

    def dfs_search(self) -> Optional[ThoughtState]:
        best_node = None
        best_score = -float("inf")

        def dfs(node: ThoughtState):
            nonlocal best_node, best_score
            if node.score > best_score:
                best_score = node.score
                best_node = node
            if node.depth >= self.max_depth:
                return
            thoughts = self.generate_thoughts_fn(node.content, self.branching_factor)
            for thought in thoughts:
                score = self.evaluate_fn(thought)
                child = ThoughtState(content=thought, score=score, depth=node.depth + 1, parent=node)
                node.children.append(child)
                dfs(child)

        root = ThoughtState(content=self.initial_state, depth=0)
        root.score = self.evaluate_fn(root.content)
        dfs(root)
        return best_node

    def search(self, mode: str = "bfs") -> Optional[ThoughtState]:
        if mode == "bfs":
            return self.bfs_search()
        elif mode == "dfs":
            return self.dfs_search()
        else:
            raise ValueError(f"Unknown mode: {mode}")
