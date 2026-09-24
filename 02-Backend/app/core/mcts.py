"""
Monte Carlo Tree Search (MCTS) for chain-of-thought reasoning.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Node:
    state: str
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)
    visit_count: int = 0
    value: float = 0.0
    prior: float = 0.0
    action: Optional[str] = None
    depth: int = 0

    def is_expanded(self) -> bool:
        return len(self.children) > 0

    def is_terminal(self) -> bool:
        return self.state.lower() in {"stop", "end", "done"}

    def get_uct(self, c_puct: float = 1.5) -> float:
        if self.visit_count == 0:
            return float("inf")
        return self.value + c_puct * self.prior * math.sqrt(self.parent.visit_count if self.parent else 1) / (1 + self.visit_count)


class ValueModel:
    """Simple value model for scoring intermediate reasoning steps."""

    def __init__(self):
        self.weights = np.random.randn(10, 1) * 0.01

    def score(self, state: str) -> float:
        features = np.array([len(state), state.count(" "), state.count("."), state.count("!"), state.count("?"), state.count(","), state.count("0"), state.count("1"), state.count("2"), state.count("3")])
        score = float((features @ self.weights).item())
        return float(math.tanh(score))


class MCTS:
    """Monte Carlo Tree Search for reasoning."""

    def __init__(self, value_model: Optional[ValueModel] = None, c_puct: float = 1.5, num_simulations: int = 50):
        self.value_model = value_model or ValueModel()
        self.c_puct = c_puct
        self.num_simulations = num_simulations

    def search(self, root_state: str, get_actions, max_depth: int = 5) -> Node:
        root = Node(state=root_state)
        for _ in range(self.num_simulations):
            node = self._select(root)
            if node.is_terminal() or node.depth >= max_depth:
                value = self.value_model.score(node.state)
                self._backpropagate(node, value)
            else:
                actions = get_actions(node.state)
                for action in actions[:3]:
                    child_state = node.state + " -> " + action
                    child = Node(state=child_state, parent=node, action=action, prior=1.0 / max(len(actions), 1))
                    node.children.append(child)
                if node.children:
                    child = np.random.choice(node.children)
                    value = self.value_model.score(child.state)
                    self._backpropagate(child, value)
        return max(root.children, key=lambda c: c.visit_count) if root.children else root

    def _select(self, node: Node) -> Node:
        while node.is_expanded() and not node.is_terminal():
            node = max(node.children, key=lambda c: c.get_uct(self.c_puct))
        return node

    def _backpropagate(self, node: Node, value: float):
        while node is not None:
            node.visit_count += 1
            node.value += (value - node.value) / node.visit_count
            node = node.parent


def tree_search_reasoning(prompt: str, depth: int = 3, breadth: int = 3) -> Dict[str, Any]:
    def get_actions(state: str) -> List[str]:
        return [f"Step {i+1}" for i in range(breadth)]
    mcts = MCTS(num_simulations=20)
    best_node = mcts.search(prompt, get_actions=get_actions, max_depth=depth)
    return {
        "prompt": prompt,
        "best_action": best_node.action,
        "best_state": best_node.state,
        "visits": best_node.visit_count,
        "value": best_node.value,
    }
