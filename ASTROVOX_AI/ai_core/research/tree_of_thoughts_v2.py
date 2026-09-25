"""
Tree of Thoughts for systematic exploration and reasoning.
"""

from __future__ import annotations

import logging
import math
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class TreeNode:
    def __init__(self, value: str, parent: Optional['TreeNode'] = None, children: Optional[List['TreeNode']] = None):
        self.value = value
        self.parent = parent
        self.children = children or []
        self.visits = 0
        self.value_sum = 0.0

    def ucb(self, exploration: float = 1.0) -> float:
        if self.visits == 0:
            return float('inf')
        exploitation = self.value_sum / self.visits
        if self.parent is None:
            return exploitation
        exploration_term = exploration * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration_term

    def expand(self, children: List[str]) -> List['TreeNode']:
        new_nodes = [TreeNode(child, parent=self) for child in children]
        self.children.extend(new_nodes)
        return new_nodes

    def best_child(self, exploration: float = 1.0) -> Optional['TreeNode']:
        if not self.children:
            return None
        return max(self.children, key=lambda n: n.ucb(exploration))

    def is_fully_expanded(self, expected_children: int) -> bool:
        return len(self.children) >= expected_children


class TreeOfThoughts:
    def __init__(self, max_depth: int = 6, branching_factor: int = 3, exploration: float = 1.0, score_fn: Optional[callable] = None):
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.exploration = exploration
        self.score_fn = score_fn or (lambda x: len(x.split()))
        self.root: Optional[TreeNode] = None
        self.solution_nodes: List[TreeNode] = []

    def search(self, initial_state: str, generate_fn: callable, evaluate_fn: callable, num_iterations: int = 50) -> Optional[TreeNode]:
        self.root = TreeNode(initial_state)
        for _ in range(num_iterations):
            leaf = self._select(self.root)
            if leaf is None:
                continue
            if leaf.visits == 0:
                score = evaluate_fn(leaf.value)
                leaf.value_sum += score
                leaf.visits += 1
                if self.score_fn(leaf.value) > 0.8:
                    self.solution_nodes.append(leaf)
            else:
                children = generate_fn(leaf.value, self.branching_factor)
                if children:
                    new_children = leaf.expand(children)
                    for child in new_children:
                        score = evaluate_fn(child.value)
                        child.value_sum += score
                        child.visits += 1
                leaf.visits += 1
        if self.solution_nodes:
            return max(self.solution_nodes, key=lambda n: n.value_sum / max(n.visits, 1))
        if self.root and self.root.children:
            return max(self.root.children, key=lambda n: n.value_sum / max(n.visits, 1))
        return self.root

    def _select(self, node: TreeNode) -> Optional[TreeNode]:
        current = node
        while current.is_fully_expanded(self.branching_factor) and current.children:
            current = current.best_child(self.exploration)
        return current

    def get_best_solution(self) -> Optional[str]:
        if not self.solution_nodes:
            return None
        best = max(self.solution_nodes, key=lambda n: n.value_sum / max(n.visits, 1))
        return best.value

    def get_all_solutions(self) -> List[str]:
        return [node.value for node in self.solution_nodes]
