import random
import math
from typing import Any, Optional, List, Dict


class MCTSNode:
    def __init__(self, state: Any, parent: Optional["MCTSNode"] = None, action: Any = None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children: List["MCTSNode"] = []
        self.visits = 0
        self.value = 0.0
        self.untried_actions: List[Any] = []

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    def is_terminal(self) -> bool:
        return self.state.get("terminal", False) or len(self.untried_actions) == 0

    def best_child(self, exploration_constant: float = 1.414) -> "MCTSNode":
        best_score = -float("inf")
        best_node = None
        for child in self.children:
            if child.visits == 0:
                return child
            exploit = child.value / child.visits
            explore = exploration_constant * math.sqrt(math.log(self.visits) / child.visits)
            uct = exploit + explore
            if uct > best_score:
                best_score = uct
                best_node = child
        return best_node

    def expand(self, action: Any, next_state: Any) -> "MCTSNode":
        child = MCTSNode(state=next_state, parent=self, action=action)
        self.children.append(child)
        self.untried_actions.remove(action)
        return child

    def backpropagate(self, reward: float) -> None:
        self.visits += 1
        self.value += reward
        if self.parent:
            self.parent.backpropagate(reward)


class MCTS:
    def __init__(
        self,
        initial_state: Any,
        get_actions_fn,
        apply_action_fn,
        evaluate_fn,
        max_iterations: int = 100,
    ):
        self.root = MCTSNode(state=initial_state)
        self.root.untried_actions = get_actions_fn(initial_state)
        self.get_actions_fn = get_actions_fn
        self.apply_action_fn = apply_action_fn
        self.evaluate_fn = evaluate_fn
        self.max_iterations = max_iterations

    def select(self, node: MCTSNode) -> MCTSNode:
        while not node.is_terminal() and node.is_fully_expanded():
            node = node.best_child()
        return node

    def expand(self, node: MCTSNode) -> Optional[MCTSNode]:
        if node.is_terminal():
            return None
        action = random.choice(node.untried_actions)
        next_state = self.apply_action_fn(node.state, action)
        return node.expand(action, next_state)

    def simulate(self, node: MCTSNode) -> float:
        current_state = node.state
        depth = 0
        max_depth = 10
        while not current_state.get("terminal", False) and depth < max_depth:
            actions = self.get_actions_fn(current_state)
            if not actions:
                break
            action = random.choice(actions)
            current_state = self.apply_action_fn(current_state, action)
            depth += 1
        return self.evaluate_fn(current_state)

    def search(self) -> Any:
        for _ in range(self.max_iterations):
            node = self.select(self.root)
            leaf = self.expand(node)
            if leaf is None:
                leaf = node
            reward = self.simulate(leaf)
            leaf.backpropagate(reward)
        if not self.root.children:
            return None
        best = max(self.root.children, key=lambda c: c.visits)
        return best.action
