from __future__ import annotations

from typing import Any, List


from reasoning_scaffolds.mcts import MCTSNode, mcts_search


def test_mcts_node_uct():
    root = MCTSNode(state=0)
    root.visits = 10
    child = MCTSNode(state=1, parent=root)
    child.visits = 2
    child.value = 1
    uct = child.uct(1.0)
    assert uct > 0


def test_mcts_search_simple():
    def expand(state: Any) -> List[Any]:
        return [state + 1]

    def simulate(state: Any) -> float:
        return float(state)

    def factory(state: Any, action: Any) -> Any:
        return action

    best = mcts_search(0, expand, simulate, factory, n_iterations=10)
    assert best is not None


def test_mcts_node_backpropagate():
    root = MCTSNode(state=0)
    child = MCTSNode(state=1, parent=root)
    root.visits = 1
    child.backpropagate(1.0)
    assert child.value == 1.0
    assert child.visits == 1
    assert root.value == 1.0
