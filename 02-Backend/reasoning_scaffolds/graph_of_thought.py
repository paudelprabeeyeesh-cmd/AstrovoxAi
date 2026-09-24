from __future__ import annotations

from typing import Callable, Dict, List, Optional


class ThoughtGraph:
    def __init__(self, problem: str) -> None:
        self.problem = problem
        self.nodes: List[str] = []
        self.edges: List[tuple] = []
        self.node_scores: Dict[str, float] = {}

    def add_thought(self, thought: str, score: float = 0.0) -> int:
        self.nodes.append(thought)
        self.node_scores[thought] = score
        return len(self.nodes) - 1

    def connect(self, source_idx: int, target_idx: int) -> None:
        if 0 <= source_idx < len(self.nodes) and 0 <= target_idx < len(self.nodes):
            self.edges.append((source_idx, target_idx))

    def merge_thoughts(
        self,
        thought_a: str,
        thought_b: str,
        combine_fn: Callable[[str, str], str],
        score_fn: Callable[[str], float],
    ) -> str:
        merged = combine_fn(thought_a, thought_b)
        self.add_thought(merged, score_fn(merged))
        return merged

    def split_thought(
        self,
        thought: str,
        split_fn: Callable[[str], List[str]],
        score_fn: Callable[[str], float],
    ) -> List[str]:
        children = split_fn(thought)
        results = []
        for child in children:
            self.add_thought(child, score_fn(child))
            results.append(child)
        return results

    def best_thought(self) -> Optional[str]:
        if not self.nodes:
            return None
        return max(self.nodes, key=lambda t: self.node_scores.get(t, 0.0))

    def search(
        self,
        expand_fn: Callable[[str], List[str]],
        score_fn: Callable[[str], float],
        max_iterations: int = 5,
    ) -> Optional[str]:
        current = self.problem
        for _ in range(max_iterations):
            successors = expand_fn(current)
            if not successors:
                break
            current = max(successors, key=score_fn)
        return current
