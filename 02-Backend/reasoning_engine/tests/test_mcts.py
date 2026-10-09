import random
from reasoning_engine.mcts import MCTSNode, MCTS


def _simple_actions(state):
    return state.get("actions", [])


def _simple_apply(state, action):
    next_state = dict(state)
    next_state["terminal"] = True
    next_state["last_action"] = action
    return next_state


def _simple_evaluate(state):
    return float(state.get("value", 0.0))


def test_mcts_node_initialization():
    state = {"actions": ["a", "b"], "value": 1.0}
    node = MCTSNode(state=state, action="start")
    assert node.visits == 0
    assert node.value == 0.0
    assert node.parent is None
    assert node.action == "start"


def test_mcts_node_expand():
    state = {"actions": ["a", "b"], "terminal": False}
    node = MCTSNode(state=state)
    node.untried_actions = ["a", "b"]
    child = node.expand("a", {"terminal": True, "value": 2.0})
    assert child.parent == node
    assert child.action == "a"
    assert child.state == {"terminal": True, "value": 2.0}
    assert "a" not in node.untried_actions
    assert "b" in node.untried_actions


def test_mcts_node_backpropagate():
    state = {"actions": [], "value": 5.0}
    node = MCTSNode(state=state)
    node.backpropagate(3.0)
    assert node.visits == 1
    assert node.value == 3.0
    node.backpropagate(7.0)
    assert node.visits == 2
    assert node.value == 10.0


def test_mcts_node_uct_selection():
    state = {"actions": [], "value": 0.0}
    root = MCTSNode(state=state)
    root.visits = 10
    child1 = MCTSNode(state={}, parent=root, action="a")
    child1.visits = 5
    child1.value = 10.0
    child2 = MCTSNode(state={}, parent=root, action="b")
    child2.visits = 5
    child2.value = 0.0
    root.children = [child1, child2]
    best = root.best_child(exploration_constant=1.414)
    assert best == child1


def test_mcts_search_returns_action():
    initial = {"actions": ["left", "right"], "terminal": False}
    mcts = MCTS(
        initial_state=initial,
        get_actions_fn=_simple_actions,
        apply_action_fn=_simple_apply,
        evaluate_fn=_simple_evaluate,
        max_iterations=20,
    )
    action = mcts.search()
    assert action in ["left", "right"]


def test_mcts_search_deterministic_with_seed():
    random.seed(42)
    initial = {"actions": ["a", "b"], "terminal": False, "value": 3.0}
    mcts = MCTS(
        initial_state=initial,
        get_actions_fn=_simple_actions,
        apply_action_fn=_simple_apply,
        evaluate_fn=_simple_evaluate,
        max_iterations=50,
    )
    result = mcts.search()
    assert result is not None


def test_mcts_simulation_reaches_terminal():
    initial = {"actions": ["go"], "terminal": False, "value": 7.0}
    mcts = MCTS(
        initial_state=initial,
        get_actions_fn=_simple_actions,
        apply_action_fn=_simple_apply,
        evaluate_fn=_simple_evaluate,
        max_iterations=10,
    )
    node = mcts.root
    node.untried_actions = ["go"]
    expanded = mcts.expand(node)
    reward = mcts.simulate(expanded)
    assert isinstance(reward, float)


def test_mcts_terminal_node_no_expand():
    terminal_state = {"terminal": True}
    node = MCTSNode(state=terminal_state)
    assert node.is_terminal() is True
    expanded = MCTS(
        initial_state=terminal_state,
        get_actions_fn=lambda s: [],
        apply_action_fn=lambda s, a: s,
        evaluate_fn=lambda s: 0.0,
    ).expand(node)
    assert expanded is None
