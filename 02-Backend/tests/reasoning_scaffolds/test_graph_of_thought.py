from __future__ import annotations

import pytest

from reasoning_scaffolds.graph_of_thought import ThoughtGraph


def fake_combine(a: str, b: str) -> str:
    return f"{a}+{b}"


def fake_split(thought: str) -> list[str]:
    return [f"{thought}.1", f"{thought}.2"]


def fake_score(thought: str) -> float:
    return float(len(thought))


def test_thought_graph_add_and_best():
    g = ThoughtGraph("problem")
    idx0 = g.add_thought("idea-a", 1.0)
    idx1 = g.add_thought("idea-b", 2.0)
    assert g.best_thought() == "idea-b"


def test_thought_graph_connect():
    g = ThoughtGraph("problem")
    i0 = g.add_thought("a")
    i1 = g.add_thought("b")
    g.connect(i0, i1)
    assert (i0, i1) in g.edges


def test_thought_graph_merge():
    g = ThoughtGraph("problem")
    merged = g.merge_thoughts("a", "b", fake_combine, fake_score)
    assert merged == "a+b"
    assert merged in g.nodes


def test_thought_graph_split():
    g = ThoughtGraph("problem")
    children = g.split_thought("node", fake_split, fake_score)
    assert children == ["node.1", "node.2"]
    assert all(c in g.nodes for c in children)


def test_thought_graph_search():
    g = ThoughtGraph("problem")
    g.add_thought("start", 0.0)
    result = g.search(lambda t: [f"{t}-next"], lambda t: float(len(t)), max_iterations=2)
    assert result is not None
