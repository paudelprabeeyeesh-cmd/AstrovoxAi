import numpy as np
import pytest
from reasoning_engine.tree_of_thoughts import ToTSearch, ThoughtState


def _generate_thoughts(content: str, n: int):
    return [f"{content} -> thought_{i}" for i in range(n)]


def _evaluate(content: str):
    return float(len(content))


def test_tot_bfs_search():
    tot = ToTSearch(
        initial_state="start",
        generate_thoughts_fn=_generate_thoughts,
        evaluate_fn=_evaluate,
        max_depth=2,
        branching_factor=3,
        beam_width=2,
    )
    best = tot.bfs_search()
    assert best is not None
    assert best.depth <= 2


def test_tot_dfs_search():
    tot = ToTSearch(
        initial_state="start",
        generate_thoughts_fn=_generate_thoughts,
        evaluate_fn=_evaluate,
        max_depth=2,
        branching_factor=2,
        beam_width=2,
    )
    best = tot.dfs_search()
    assert best is not None


def test_tot_search_modes():
    tot = ToTSearch(
        initial_state="root",
        generate_thoughts_fn=_generate_thoughts,
        evaluate_fn=_evaluate,
        max_depth=3,
        branching_factor=4,
        beam_width=3,
    )
    bfs_best = tot.search(mode="bfs")
    dfs_best = tot.search(mode="dfs")
    assert bfs_best is not None
    assert dfs_best is not None


def test_tot_invalid_mode():
    tot = ToTSearch(
        initial_state="x",
        generate_thoughts_fn=_generate_thoughts,
        evaluate_fn=_evaluate,
        max_depth=1,
        branching_factor=1,
        beam_width=1,
    )
    with pytest.raises(ValueError):
        tot.search(mode="invalid")


def test_thought_state_repr():
    ts = ThoughtState(content="hello", score=0.5, depth=2)
    r = repr(ts)
    assert "hello" in r
    assert "0.5" in r


def test_tot_evaluation_numerical():
    def score_fn(x):
        return float(x.count("a"))

    tot = ToTSearch(
        initial_state="aaa",
        generate_thoughts_fn=lambda c, n: [c + "a" for _ in range(n)],
        evaluate_fn=score_fn,
        max_depth=1,
        branching_factor=2,
        beam_width=2,
    )
    best = tot.bfs_search()
    assert best.score >= 3.0
