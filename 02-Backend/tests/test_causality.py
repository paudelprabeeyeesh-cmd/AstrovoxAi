import pytest
import numpy as np
from causality.causal_engine import CausalEngine, CausalNode, CausalEdge


class TestCausalEngine:
    def test_add_nodes_and_edges(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="x", variable="X"))
        engine.add_node(CausalNode(id="y", variable="Y"))
        engine.add_edge(CausalEdge(source="x", target="y", strength=0.8, sign="positive"))
        assert engine.causal_strength("x", "y") == 0.8

    def test_learn_from_interventions(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="x", variable="X"))
        engine.add_node(CausalNode(id="y", variable="Y"))
        engine.add_edge(CausalEdge(source="x", target="y", strength=0.5, sign="positive"))
        avg = engine.learn_from_interventions([("x", 10.0)], [("y", 8.0)])
        assert 0.0 <= avg <= 1.0
        assert abs(engine.causal_strength("x", "y") - 0.8) < 0.01

    def test_intervention_effect(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="x", variable="X"))
        engine.add_node(CausalNode(id="y", variable="Y"))
        engine.add_node(CausalNode(id="z", variable="Z"))
        engine.add_edge(CausalEdge(source="x", target="y", strength=0.5, sign="positive"))
        engine.add_edge(CausalEdge(source="y", target="z", strength=0.5, sign="positive"))
        effect = engine.intervention_effect("z", "x", 10.0)
        assert effect == pytest.approx(2.5)

    def test_backdoor_adjustment(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="o", variable="Outcome"))
        engine.add_node(CausalNode(id="c", variable="Confounder"))
        engine.add_edge(CausalEdge(source="t", target="o", strength=0.9, sign="positive"))
        engine.add_edge(CausalEdge(source="c", target="t", strength=0.6, sign="positive"))
        engine.add_edge(CausalEdge(source="c", target="o", strength=0.5, sign="positive"))
        adjusted = engine.backdoor_adjustment("t", "o", ["c"])
        assert adjusted >= 0.0

    def test_counterfactual(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="x", variable="X"))
        engine.add_node(CausalNode(id="y", variable="Y"))
        engine.add_edge(CausalEdge(source="x", target="y", strength=0.8, sign="positive"))
        val = engine.counterfactual({"x": 5.0}, "y")
        assert val == pytest.approx(4.0)

    def test_no_path_returns_none(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="a", variable="A"))
        engine.add_node(CausalNode(id="b", variable="B"))
        assert engine.intervention_effect("b", "a", 10.0) == 0.0
