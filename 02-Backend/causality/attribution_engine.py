from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from causality.causal_graph import CausalGraph, CausalEdge


@dataclass
class Attribution:
    variable: str
    total_effect: float
    direct_effect: float
    indirect_effect: float
    path_count: int
    share: float


class AttributionEngine:
    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def attribute_effect(self, treatment: str, outcome: str, intervention_value: float = 1.0) -> List[Attribution]:
        if treatment not in self.graph.nodes or outcome not in self.graph.nodes:
            return []
        paths = self.graph.find_paths(treatment, outcome, max_paths=50)
        if not paths:
            return []

        total_effect = 0.0
        path_effects: List[Tuple[List[str], float]] = []
        for path in paths:
            effect = intervention_value
            valid = True
            for i in range(len(path) - 1):
                src, tgt = path[i], path[i + 1]
                edge = next((e for e in self.graph.edges if e.source == src and e.target == tgt), None)
                if edge:
                    effect *= edge.strength * (1.0 if edge.sign == "positive" else -1.0)
                else:
                    valid = False
                    break
            if valid:
                total_effect += effect
                path_effects.append((path, effect))

        node_effects: Dict[str, float] = {}
        node_counts: Dict[str, int] = {}
        for path, effect in path_effects:
            for node in path[1:-1]:
                node_effects[node] = node_effects.get(node, 0.0) + effect
                node_counts[node] = node_counts.get(node, 0) + 1

        direct = self.direct_effect(treatment, outcome)

        attributions: List[Attribution] = []
        for var, eff in sorted(node_effects.items(), key=lambda x: abs(x[1]), reverse=True):
            attributions.append(Attribution(
                variable=var,
                total_effect=total_effect,
                direct_effect=direct if var == outcome else 0.0,
                indirect_effect=eff,
                path_count=node_counts.get(var, 0),
                share=eff / total_effect if total_effect != 0 else 0.0,
            ))
        return attributions

    def total_effect(self, treatment: str, outcome: str, intervention_value: float = 1.0) -> float:
        paths = self.graph.find_paths(treatment, outcome, max_paths=50)
        effect = 0.0
        for path in paths:
            current = intervention_value
            valid = True
            for i in range(len(path) - 1):
                src, tgt = path[i], path[i + 1]
                edge = next((e for e in self.graph.edges if e.source == src and e.target == tgt), None)
                if edge:
                    current *= edge.strength * (1.0 if edge.sign == "positive" else -1.0)
                else:
                    valid = False
                    break
            if valid:
                effect += current
        return effect

    def direct_effect(self, treatment: str, outcome: str) -> float:
        return sum(e.strength for e in self.graph.edges if e.source == treatment and e.target == outcome)
