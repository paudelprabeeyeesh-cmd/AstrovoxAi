import pytest
import numpy as np
from datetime import datetime, timedelta
from complex_reasoning.causal_reasoning import CausalNode, CausalEdge, CausalGraph, CausalEngine


class TestCausalGraph:
    def test_add_nodes_and_edges(self):
        g = CausalGraph()
        g.add_node(CausalNode("A"))
        g.add_node(CausalNode("B"))
        g.add_edge(CausalEdge("A", "B", strength=0.8))
        assert len(g.nodes) == 2
        assert len(g.edges) == 1

    def test_do_calculus(self):
        g = CausalGraph()
        g.add_node(CausalNode("A"))
        g.add_node(CausalNode("B"))
        g.add_edge(CausalEdge("A", "B", strength=0.8))
        effect = g.do_calculus("A", "B", 1.0)
        assert effect != 0.0

    def test_total_effect(self):
        g = CausalGraph()
        g.add_node(CausalNode("X"))
        g.add_node(CausalNode("Y"))
        g.add_edge(CausalEdge("X", "Y", strength=0.5))
        te = g.total_effect("X", "Y")
        assert te != 0.0

    def test_counterfactual(self):
        g = CausalGraph()
        g.add_node(CausalNode("X"))
        g.add_node(CausalNode("Y"))
        g.add_edge(CausalEdge("X", "Y", strength=0.7))
        result = g.counterfactual({"X": 1.0, "Y": 0.5}, "Y", {"X": 1.0})
        assert isinstance(result, float)


class TestCausalEngine:
    def test_add_node_and_edge(self):
        engine = CausalEngine()
        engine.add_node(CausalNode("A"))
        engine.add_edge(CausalEdge("A", "B"))
        assert engine.causal_strength("A", "B") == 1.0

    def test_backdoor_adjustment(self):
        engine = CausalEngine()
        engine.add_node(CausalNode("X"))
        engine.add_node(CausalNode("Y"))
        engine.add_node(CausalNode("Z"))
        engine.add_edge(CausalEdge("Z", "X"))
        engine.add_edge(CausalEdge("Z", "Y"))
        result = engine.backdoor_adjustment("X", "Y", ["Z"])
        assert isinstance(result, float)
