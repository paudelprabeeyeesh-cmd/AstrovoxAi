import pytest
from causality.causal_graph import CausalGraph, CausalNode, CausalEdge
from causality.attribution_engine import AttributionEngine, Attribution


class TestAttributionEngine:
    def test_total_effect(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="positive"))
        engine = AttributionEngine(graph)
        assert engine.total_effect("t", "y", intervention_value=2.0) == pytest.approx(1.6)

    def test_direct_effect(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="positive"))
        engine = AttributionEngine(graph)
        assert engine.direct_effect("t", "y") == pytest.approx(0.8)

    def test_attribute_effect(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="m", variable="Mediator"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_edge(CausalEdge(source="t", target="m", strength=0.8, sign="positive"))
        graph.add_edge(CausalEdge(source="m", target="y", strength=0.8, sign="positive"))
        engine = AttributionEngine(graph)
        attributions = engine.attribute_effect("t", "y", intervention_value=1.0)
        assert len(attributions) > 0
        assert any(a.variable == "m" for a in attributions)
