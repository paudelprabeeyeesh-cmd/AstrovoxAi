from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class CausalNode:
    id: str
    variable: str
    observed: bool = True
    value: Optional[float] = None


@dataclass
class CausalEdge:
    source: str
    target: str
    strength: float = 1.0
    sign: str = "positive"


class CausalEngine:
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self.adjacency: Dict[str, List[Tuple[str, float]]] = {}

    def add_node(self, node: CausalNode) -> None:
        self.nodes[node.id] = node
        self.adjacency.setdefault(node.id, [])

    def add_edge(self, edge: CausalEdge) -> None:
        self.edges.append(edge)
        self.adjacency.setdefault(edge.source, []).append((edge.target, edge.strength))
        self.adjacency.setdefault(edge.target, [])

    def learn_from_interventions(self, interventions: List[Tuple[str, float]], outcomes: List[Tuple[str, float]]) -> float:
        if len(interventions) != len(outcomes):
            raise ValueError("Interventions and outcomes must match")
        learned = []
        for (intv_id, intv_val), (out_id, out_val) in zip(interventions, outcomes):
            for edge in self.edges:
                if edge.source == intv_id and edge.target == out_id:
                    edge.strength = max(0.0, min(1.0, out_val / max(intv_val, 1e-6)))
                    learned.append(edge.strength)
        return float(np.mean(learned)) if learned else 0.0

    def intervention_effect(self, target_id: str, intervention_id: str, intervention_value: float) -> float:
        if target_id not in self.adjacency:
            return 0.0
        path = self._find_path(intervention_id, target_id)
        if not path:
            return 0.0
        effect = intervention_value
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            edge = next((e for e in self.edges if e.source == src and e.target == tgt), None)
            if edge:
                effect *= edge.strength * (1.0 if edge.sign == "positive" else -1.0)
        return effect

    def _find_path(self, start: str, end: str) -> Optional[List[str]]:
        if start not in self.adjacency or end not in self.adjacency:
            return None
        queue = [(start, [start])]
        visited = {start}
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            for neighbor, _ in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def backdoor_adjustment(self, treatment: str, outcome: str, confounders: List[str]) -> float:
        direct_edges = [e for e in self.edges if e.source == treatment and e.target == outcome]
        if not direct_edges:
            return 0.0
        direct = sum(e.strength for e in direct_edges)
        confounder_effect = 0.0
        for c in confounders:
            t_edges = [e for e in self.edges if e.source == c and e.target == treatment]
            o_edges = [e for e in self.edges if e.source == c and e.target == outcome]
            confounder_effect += sum(e.strength for e in t_edges) * sum(e.strength for e in o_edges)
        return max(0.0, direct - confounder_effect)

    def counterfactual(self, scenario: Dict[str, float], target: str) -> Optional[float]:
        if target not in self.nodes:
            return None
        value = 0.0
        incoming = [e for e in self.edges if e.target == target]
        for edge in incoming:
            src_val = scenario.get(edge.source, 0.0)
            value += edge.strength * src_val * (1.0 if edge.sign == "positive" else -1.0)
        return value

    def causal_strength(self, source: str, target: str) -> float:
        edge = next((e for e in self.edges if e.source == source and e.target == target), None)
        return edge.strength if edge else 0.0
