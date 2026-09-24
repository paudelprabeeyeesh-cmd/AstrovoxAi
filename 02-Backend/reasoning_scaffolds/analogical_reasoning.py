from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


class Analogy:
    def __init__(self, source: str, target: str, relations: List[Tuple[str, str]]) -> None:
        self.source = source
        self.target = target
        self.relations = relations

    def map_element(self, element: str) -> Optional[str]:
        mapping = {k: v for k, v in self.relations}
        return mapping.get(element)


def analogical_reason(
    problem: str,
    base_cases: List[Dict[str, Any]],
    retrieve_fn: Callable[[str, List[Dict[str, Any]]], Analogy],
    map_fn: Callable[[Analogy, Dict[str, Any]], Dict[str, Any]],
    transfer_fn: Callable[[Dict[str, Any]], Optional[str]],
) -> Optional[str]:
    analogy = retrieve_fn(problem, base_cases)
    if analogy is None:
        return None
    mapped = map_fn(analogy, {"problem": problem})
    return transfer_fn(mapped)


def retrieve_analogy(problem: str, base_cases: List[Dict[str, Any]]) -> Analogy:
    scored = []
    for case in base_cases:
        score = _similarity(problem, case.get("description", ""))
        scored.append((score, case))
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1] if scored else {}
    relations = best.get("relations", [])
    return Analogy(source=best.get("source", ""), target=best.get("target", ""), relations=relations)


def _similarity(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / (len(set_a | set_b) + 1e-8)
