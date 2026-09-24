import numpy as np
from typing import List, Dict, Optional, Set


class CausalNode:
    def __init__(self, name: str, node_type: str = "variable", prior: float = 0.1):
        self.name = name
        self.node_type = node_type
        self.prior = prior
        self.value: float = 0.0
        self.children: List["CausalEdge"] = []
        self.parents: List["CausalEdge"] = []

    def update_value(self, value: float):
        self.value = value

    def structural_equation(self, parents: List["CausalNode"]) -> float:
        if not parents:
            return self.prior
        return np.clip(np.mean([p.value for p in parents]) + np.random.normal(0, 0.1), 0, 1)


class CausalEdge:
    def __init__(self, source: str, target: str, strength: float = 1.0, mechanism: str = "linear"):
        self.source = source
        self.target = target
        self.strength = strength
        self.mechanism = mechanism

    def intervention_effect(self, source_value: float, target_value: Optional[float] = None) -> float:
        return source_value * self.strength


class CausalGraph:
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self.adj: Dict[str, List[str]] = {}

    def add_node(self, node: CausalNode):
        self.nodes[node.name] = node
        self.adj.setdefault(node.name, [])

    def add_edge(self, edge: CausalEdge):
        if edge.source not in self.nodes:
            self.nodes[edge.source] = CausalNode(edge.source)
        if edge.target not in self.nodes:
            self.nodes[edge.target] = CausalNode(edge.target)
        self.nodes[edge.source].children.append(edge)
        self.nodes[edge.target].parents.append(edge)
        self.edges.append(edge)
        self.adj.setdefault(edge.source, [])
        self.adj[edge.source].append(edge.target)

    def do_calculus(self, do_var: str, on_var: str, do_value: float) -> float:
        if do_var not in self.nodes or on_var not in self.nodes:
            return 0.0
        path_effect = self._compute_effect_along_path(do_var, on_var, do_value)
        confounders = self._find_confounders(do_var, on_var)
        adjustment = self._backdoor_adjustment(do_var, on_var, confounders, do_value)
        return path_effect + adjustment

    def _compute_effect_along_path(self, source: str, target: str, value: float) -> float:
        visited = set()
        return self._dfs_effect(source, target, value, visited)

    def _dfs_effect(self, current: str, target: str, value: float, visited: Set[str]) -> float:
        if current == target:
            return value
        if current in visited:
            return 0.0
        visited.add(current)
        total = 0.0
        for neighbor in self.adj.get(current, []):
            for edge in self.edges:
                if edge.source == current and edge.target == neighbor:
                    ev = value * edge.strength
                    total += self._dfs_effect(neighbor, target, ev, visited)
        return total

    def _find_confounders(self, x: str, y: str) -> List[str]:
        parents_x = {edge.source for edge in self.nodes[x].parents}
        parents_y = {edge.source for edge in self.nodes[y].parents}
        return list(parents_x & parents_y)

    def _backdoor_adjustment(self, x: str, y: str, confounders: List[str], do_value: float) -> float:
        if not confounders:
            return 0.0
        return sum(self._compute_effect_along_path(c, y, do_value) for c in confounders)

    def counterfactual(self, observed: Dict[str, float], query: str, intervention: Dict[str, float]) -> float:
        for name, value in intervention.items():
            if name in self.nodes:
                self.nodes[name].update_value(value)
        return self._compute_effect_along_path(list(intervention.keys())[0], query, list(intervention.values())[0])

    def total_effect(self, source: str, target: str) -> float:
        return self._compute_effect_along_path(source, target, 1.0)

    def natural_indirect_effect(self, source: str, target: str) -> float:
        return self._compute_effect_along_path(source, target, 1.0) * 0.5

    def natural_direct_effect(self, source: str, target: str) -> float:
        return self._compute_effect_along_path(source, target, 1.0) * 0.5


class CausalEngine:
    def __init__(self):
        self.graph = CausalGraph()
        self.sample_variance: Dict[str, float] = {}

    def add_node(self, node: CausalNode):
        self.graph.add_node(node)

    def add_edge(self, edge: CausalEdge):
        self.graph.add_edge(edge)

    def causal_strength(self, source: str, target: str) -> float:
        for edge in self.graph.edges:
            if edge.source == source and edge.target == target:
                return edge.strength
        return 0.0

    def do_calculus(self, do_var: str, on_var: str, do_value: float) -> float:
        return self.graph.do_calculus(do_var, on_var, do_value)

    def backdoor_adjustment(self, treatment: str, outcome: str, confounders: List[str]) -> float:
        return self.graph._backdoor_adjustment(treatment, outcome, confounders, 1.0)

    def counterfactual(self, context: Dict[str, float], query: str) -> float:
        return self.graph.counterfactual(context, query, context)

    def total_effect(self, source: str, target: str) -> float:
        return self.graph.total_effect(source, target)
