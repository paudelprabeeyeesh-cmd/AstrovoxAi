from __future__ import annotations

from typing import Optional


from reasoning_scaffolds.analogical_reasoning import (
    Analogy,
    analogical_reason,
    retrieve_analogy,
)


def test_retrieve_analogy_best_match():
    base = [
        {"source": "A", "target": "B", "description": "alpha beta", "relations": [("a1", "b1")]},
        {"source": "X", "target": "Y", "description": "x y z", "relations": [("x1", "y1")]},
    ]
    analogy = retrieve_analogy("alpha problem", base)
    assert analogy.source == "A"


def test_analogical_reason_flow():
    def retrieve_fn(problem: str, base: list[dict]) -> Analogy:
        return Analogy(source="s", target="t", relations=[("s1", "t1")])

    def map_fn(analogy: Analogy, problem: dict) -> dict:
        return {"mapped": True}

    def transfer_fn(mapped: dict) -> Optional[str]:
        return "transferred"

    result = analogical_reason("p", [], retrieve_fn, map_fn, transfer_fn)
    assert result == "transferred"


def test_analogy_map_element():
    a = Analogy("s", "t", [("s1", "t1"), ("s2", "t2")])
    assert a.map_element("s1") == "t1"
    assert a.map_element("unknown") is None
