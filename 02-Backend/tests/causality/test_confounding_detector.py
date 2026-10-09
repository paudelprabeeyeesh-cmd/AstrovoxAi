import pytest
from causality.causal_graph import CausalGraph, CausalNode, CausalEdge
from causality.confounding_detector import ConfoundingDetector, Confounder


class TestConfoundingDetector:
    def test_detect_confounders(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_node(CausalNode(id="c", variable="Confounder"))
        graph.add_edge(CausalEdge(source="c", target="t", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="y", strength=0.5, sign="positive"))
        detector = ConfoundingDetector(graph)
        confounders = detector.detect_confounders("t", "y")
        assert len(confounders) == 1
        assert confounders[0].variable == "c"
        assert confounders[0].joint_effect == pytest.approx(0.25)

    def test_is_confounded(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_node(CausalNode(id="c", variable="Confounder"))
        graph.add_edge(CausalEdge(source="c", target="t", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="y", strength=0.5, sign="positive"))
        detector = ConfoundingDetector(graph)
        assert detector.is_confounded("t", "y")
        assert not detector.is_confounded("x", "y")

    def test_backdoor_adjustment_set(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_node(CausalNode(id="c", variable="Confounder"))
        graph.add_edge(CausalEdge(source="c", target="t", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="y", strength=0.5, sign="positive"))
        detector = ConfoundingDetector(graph)
        assert detector.backdoor_adjustment_set("t", "y") == {"c"}

    def test_find_backdoor_paths(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="t", variable="Treatment"))
        graph.add_node(CausalNode(id="y", variable="Outcome"))
        graph.add_node(CausalNode(id="c", variable="Confounder"))
        graph.add_node(CausalNode(id="m", variable="Mediator"))
        graph.add_edge(CausalEdge(source="c", target="t", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="y", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="c", target="m", strength=0.5, sign="positive"))
        graph.add_edge(CausalEdge(source="m", target="y", strength=0.5, sign="positive"))
        detector = ConfoundingDetector(graph)
        paths = detector.find_backdoor_paths("t", "y")
        assert len(paths) == 2
        assert ["t", "c", "y"] in paths
        assert ["t", "c", "m", "y"] in paths
