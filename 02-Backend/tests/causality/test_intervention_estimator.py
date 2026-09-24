import pytest
from causality.causal_graph import CausalGraph, CausalNode, CausalEdge
from causality.intervention_estimator import InterventionEstimator


class TestInterventionEstimator:
    def test_estimate_effect(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="positive"))
        estimator = InterventionEstimator(graph)
        effect = estimator.estimate_effect("t", "y", intervention_value=2.0)
        assert effect == pytest.approx(1.6)

    def test_backdoor_adjustment(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_node(CausalNode(id="c", variable="Confounder"))
        graph.add_edge(CausalEdge(source="t", target="y", strength=0.9, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="t", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="y", strength=0.5, sign="positive"))
        estimator = InterventionEstimator(graph)
        effect = estimator.backdoor_adjustment("t", "y", ["c"])
        assert effect >= 0.0

    def test_frontdoor_adjustment(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_node(CausalNode(id="m", variable="Mediator"))
        graph.add_edge(CausalEdge(source="t", target="m", strength=0.7, sign="positive"))
        graph.add_edge(CausalEdge(source="m", target="y", strength=0.7, sign="positive"))
        graph.add_edge(CausalEdge(source="t", target="y", strength=0.1, sign="positive"))
        estimator = InterventionEstimator(graph)
        effect = estimator.frontdoor_adjustment("t", "y", "m")
        assert effect >= 0.0
