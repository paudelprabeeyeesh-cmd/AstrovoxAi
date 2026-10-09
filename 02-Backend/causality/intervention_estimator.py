from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from causality.causal_graph import CausalGraph, CausalEdge


class InterventionEstimator:
    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def estimate_effect(self, treatment: str, outcome: str, intervention_value: float = 1.0) -> float:
        if treatment not in self.graph.nodes or outcome not in self.graph.nodes:
            return 0.0
        effect = 0.0
        for path in self.graph.find_paths(treatment, outcome, max_paths=50):
            path_effect = intervention_value
            valid = True
            for i in range(len(path) - 1):
                src, tgt = path[i], path[i + 1]
                edge = next((e for e in self.graph.edges if e.source == src and e.target == tgt), None)
                if edge:
                    path_effect *= edge.strength * (1.0 if edge.sign == "positive" else -1.0)
                else:
                    valid = False
                    break
            if valid:
                effect += path_effect
        return effect

    def backdoor_adjustment(self, treatment: str, outcome: str, confounders: List[str]) -> float:
        direct = sum(e.strength for e in self.graph.edges if e.source == treatment and e.target == outcome)
        confounder_effect = 0.0
        for c in confounders:
            t_strength = sum(e.strength for e in self.graph.edges if e.source == c and e.target == treatment)
            o_strength = sum(e.strength for e in self.graph.edges if e.source == c and e.target == outcome)
            confounder_effect += t_strength * o_strength
        return max(0.0, direct - confounder_effect)

    def frontdoor_adjustment(
        self,
        treatment: str,
        outcome: str,
        mediator: str,
        confounders: Optional[List[str]] = None,
    ) -> float:
        tm = sum(e.strength for e in self.graph.edges if e.source == treatment and e.target == mediator)
        mo = sum(e.strength for e in self.graph.edges if e.source == mediator and e.target == outcome)
        direct = sum(e.strength for e in self.graph.edges if e.source == treatment and e.target == outcome)
        confounder_correction = 0.0
        if confounders:
            for c in confounders:
                cm = sum(e.strength for e in self.graph.edges if e.source == c and e.target == mediator)
                co = sum(e.strength for e in self.graph.edges if e.source == c and e.target == outcome)
                confounder_correction += cm * co
        return max(0.0, tm * mo + direct - confounder_correction)
