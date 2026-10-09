import pytest
from causality.causal_graph import CausalGraph, CausalNode, CausalEdge


class TestCausalGraph:
    def test_add_node_and_edge(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="x", variable="X"))
        graph.add_node(CausalNode(id="y", variable="Y"))
        graph.add_edge(CausalEdge(source="x", target="y", strength=0.8, sign="positive"))
        assert graph.edge("x", "y").strength == 0.8

    def test_remove_node(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="x", variable="X"))
        graph.add_node(CausalNode(id="y", variable="Y"))
        graph.add_edge(CausalEdge(source="x", target="y"))
        graph.remove_node("x")
        assert "x" not in graph.nodes
        assert len(graph.edges) == 0

    def test_get_descendants(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="a", variable="A"))
        graph.add_node(CausalNode(id="b", variable="B"))
        graph.add_node(CausalNode(id="c", variable="C"))
        graph.add_edge(CausalEdge(source="a", target="b"))
        graph.add_edge(CausalEdge(source="b", target="c"))
        assert graph.get_descendants("a") == {"b", "c"}
        assert graph.get_descendants("b") == {"c"}

    def test_get_ancestors(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="a", variable="A"))
        graph.add_node(CausalNode(id="b", variable="B"))
        graph.add_node(CausalNode(id="c", variable="C"))
        graph.add_edge(CausalEdge(source="a", target="b"))
        graph.add_edge(CausalEdge(source="b", target="c"))
        assert graph.get_ancestors("c") == {"a", "b"}
        assert graph.get_ancestors("b") == {"a"}

    def test_topological_sort(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="a", variable="A"))
        graph.add_node(CausalNode(id="b", variable="B"))
        graph.add_node(CausalNode(id="c", variable="C"))
        graph.add_edge(CausalEdge(source="a", target="b"))
        graph.add_edge(CausalEdge(source="b", target="c"))
        order = graph.topological_sort()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_is_acyclic(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="a", variable="A"))
        graph.add_node(CausalNode(id="b", variable="B"))
        graph.add_edge(CausalEdge(source="a", target="b"))
        assert graph.is_acyclic()
        graph.add_edge(CausalEdge(source="b", target="a"))
        assert not graph.is_acyclic()

    def test_find_paths(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="a", variable="A"))
        graph.add_node(CausalNode(id="b", variable="B"))
        graph.add_node(CausalNode(id="c", variable="C"))
        graph.add_edge(CausalEdge(source="a", target="b"))
        graph.add_edge(CausalEdge(source="b", target="c"))
        paths = graph.find_paths("a", "c")
        assert len(paths) == 1
        assert paths[0] == ["a", "b", "c"]

    def test_find_shortest_path(self):
        graph = CausalGraph()
        graph.add_node(CausalNode(id="a", variable="A"))
        graph.add_node(CausalNode(id="b", variable="B"))
        graph.add_node(CausalNode(id="c", variable="C"))
        graph.add_edge(CausalEdge(source="a", target="b"))
        graph.add_edge(CausalEdge(source="b", target="c"))
        assert graph.find_shortest_path("a", "c") == ["a", "b", "c"]
        assert graph.find_shortest_path("c", "a") is None
