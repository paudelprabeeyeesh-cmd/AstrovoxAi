from __future__ import annotations

from reasoning_scaffolds.tree_of_thought import ThoughtNode, tot_search, _ancestors


def fake_generate(parent_thought: str, history: list[str]) -> list[str]:
    return [f"{parent_thought}-child-{i}" for i in range(3)]


def fake_evaluate(thought: str, history: list[str]) -> float:
    return float(thought.count("child"))


def test_tot_search_returns_best_leaf():
    root = tot_search("root", fake_generate, fake_evaluate, depth=2, branching_factor=3, beam_width=2)
    assert root is not None
    assert "child" in root.thought


def test_tot_search_beam_width_limits_leaves():
    best = tot_search("root", fake_generate, fake_evaluate, depth=1, branching_factor=3, beam_width=1)
    assert best is not None
    assert "child" in best.thought


def test_thought_node_ancestors():
    root = ThoughtNode(thought="root")
    child = ThoughtNode(thought="child", parent=root)
    root.children.append(child)
    ancestors = [n.thought for n in _ancestors(child)]
    assert "root" in ancestors
