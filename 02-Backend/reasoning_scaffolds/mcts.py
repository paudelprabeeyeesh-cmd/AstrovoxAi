from __future__ import annotations

import math
import random
from typing import Any, Callable, Dict, List, Optional, Tuple


class MCTSNode:
    def __init__(self, state: Any, parent: Optional["MCTSNode"] = None, action: Any = None) -> None:
        self.state = state
        self.parent = parent
        self.action = action
        self.children: List["MCTSNode"] = []
        self.visits = 0
        self.value = 0.0
        self.is_terminal = False
        self.untried_actions: List[Any] = []

    def uct(self, exploration: float) -> float:
        if self.visits == 0:
            return float("inf")
        return (self.value / self.visits) + exploration * math.sqrt(math.log(self.parent.visits) / self.visits)

    def best_child(self, exploration: float) -> Optional["MCTSNode"]:
        return max(self.children, key=lambda c: c.uct(exploration)) if self.children else None

    def expand(self, action: Any, state_factory: Callable[[Any, Any], Any]) -> "MCTSNode":
        child = MCTSNode(state_factory(self.state, action), parent=self, action=action)
        self.children.append(child)
        self.untried_actions.remove(action)
        return child

    def backpropagate(self, reward: float) -> None:
        self.visits += 1
        self.value += reward
        if self.parent is not None:
            self.parent.backpropagate(reward)


def mcts_search(
    root_state: Any,
    expand_fn: Callable[[Any], List[Any]],
    simulate_fn: Callable[[Any], float],
    state_factory: Callable[[Any, Any], Any],
    n_iterations: int = 100,
    exploration_constant: float = 1.41,
) -> Optional[MCTSNode]:
    root = MCTSNode(state=root_state)
    root.untried_actions = list(expand_fn(root_state))

    for _ in range(n_iterations):
        node = _tree_policy(root, exploration_constant)
        reward = _default_policy(node, simulate_fn)
        node.backpropagate(reward)

    if root.children:
        return max(root.children, key=lambda c: c.visits)
    return root


def _tree_policy(node: MCTSNode, exploration: float) -> MCTSNode:
    while not node.is_terminal:
        if node.untried_actions:
            action = random.choice(node.untried_actions)
            return node.expand(action, _identity_state_factory())
        if node.children:
            node = node.best_child(exploration)
        else:
            break
    return node


def _default_policy(node: MCTSNode, simulate_fn: Callable[[Any], float]) -> float:
    return simulate_fn(node.state)


def _identity_state_factory() -> Callable[[Any, Any], Any]:
    def factory(state: Any, action: Any) -> Any:
        return action
    return factory
