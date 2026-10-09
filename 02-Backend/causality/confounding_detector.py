from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from causality.causal_graph import CausalGraph, CausalEdge


@dataclass
class Confounder:
    variable: str
    treatment_effect: float
    outcome_effect: float
    joint_effect: float
    confidence: float


class ConfoundingDetector:
    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def detect_confounders(self, treatment: str, outcome: str) -> List[Confounder]:
        if treatment not in self.graph.nodes or outcome not in self.graph.nodes:
            return []
        treatment_ancestors = self.graph.get_ancestors(treatment)
        outcome_ancestors = self.graph.get_ancestors(outcome)
        common = treatment_ancestors & outcome_ancestors
        confounders: List[Confounder] = []
        for var in common:
            t_effect = sum(e.strength for e in self.graph.edges if e.source == var and e.target == treatment)
            o_effect = sum(e.strength for e in self.graph.edges if e.source == var and e.target == outcome)
            if t_effect > 0 and o_effect > 0:
                confounders.append(Confounder(
                    variable=var,
                    treatment_effect=t_effect,
                    outcome_effect=o_effect,
                    joint_effect=t_effect * o_effect,
                    confidence=min(t_effect, o_effect),
                ))
        return sorted(confounders, key=lambda c: c.joint_effect, reverse=True)

    def backdoor_adjustment_set(self, treatment: str, outcome: str) -> Set[str]:
        return {c.variable for c in self.detect_confounders(treatment, outcome)}

    def is_confounded(self, treatment: str, outcome: str) -> bool:
        return len(self.detect_confounders(treatment, outcome)) > 0

    def find_backdoor_paths(self, treatment: str, outcome: str, max_paths: int = 20) -> List[List[str]]:
        if treatment not in self.graph.nodes or outcome not in self.graph.nodes:
            return []
        paths: List[List[str]] = []
        for edge in self.graph.edges:
            if edge.target == treatment:
                z = edge.source
                sub = self._undirected_paths(z, outcome, max_paths)
                for p in sub:
                    paths.append([treatment, z] + p[1:])
        return paths

    def _undirected_paths(self, start: str, end: str, max_paths: int = 20) -> List[List[str]]:
        result: List[List[str]] = []
        stack = [(start, [start])]
        while stack and len(result) < max_paths:
            current, path = stack.pop()
            if current == end:
                result.append(path)
                continue
            neighbors: List[str] = []
            for e in self.graph.edges:
                if e.source == current:
                    neighbors.append(e.target)
                if e.target == current:
                    neighbors.append(e.source)
            for n in neighbors:
                if n not in path:
                    stack.append((n, path + [n]))
        return result

    def adjusts_confounding(self, treatment: str, outcome: str, adjustment_set: Set[str]) -> bool:
        if treatment not in self.graph.nodes or outcome not in self.graph.nodes:
            return False
        valid = {a for a in adjustment_set if a in self.graph.nodes}
        if not valid:
            return True
        backdoor_paths = self.find_backdoor_paths(treatment, outcome, max_paths=50)
        for path in backdoor_paths:
            blocked = any(node in valid for node in path[1:-1])
            if not blocked:
                return False
        return True
