import pytest
from knowledge_graph.query_engine import QueryEngine
from knowledge_graph.knowledge_graph import Entity, Relation


class TestQueryEngine:
    def test_find_entity(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="e1", name="Alice", type="person"))
        entity = engine.find_entity("Alice")
        assert entity is not None
        assert entity.id == "e1"

    def test_neighbors(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="e1", name="A", type="t"))
        engine.graph.add_entity(Entity(id="e2", name="B", type="t"))
        engine.graph.add_relation(Relation(source="e1", target="e2", type="knows"))
        neighbors = engine.neighbors("e1")
        assert neighbors == [("e2", "knows", 1.0)]

    def test_neighbors_filtered(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="e1", name="A", type="t"))
        engine.graph.add_entity(Entity(id="e2", name="B", type="t"))
        engine.graph.add_relation(Relation(source="e1", target="e2", type="knows"))
        neighbors = engine.neighbors("e1", relation_type="knows")
        assert len(neighbors) == 1
        assert engine.neighbors("e1", relation_type="other") == []

    def test_path(self):
        engine = QueryEngine()
        for i in range(3):
            engine.graph.add_entity(Entity(id=f"n{i}", name=f"N{i}", type="node"))
        engine.graph.add_relation(Relation(source="n0", target="n1", type="link"))
        engine.graph.add_relation(Relation(source="n1", target="n2", type="link"))
        assert engine.path("n0", "n2") == ["n0", "n1", "n2"]

    def test_subgraph(self):
        engine = QueryEngine()
        for i in range(3):
            engine.graph.add_entity(Entity(id=f"n{i}", name=f"N{i}", type="node"))
        engine.graph.add_relation(Relation(source="n0", target="n1", type="link"))
        engine.graph.add_relation(Relation(source="n1", target="n2", type="link"))
        nodes, edges = engine.subgraph("n1", depth=1)
        assert "n1" in nodes
        assert "n0" in nodes
        assert "n2" in nodes

    def test_connected_component(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        engine.graph.add_entity(Entity(id="c", name="C", type="t"))
        engine.graph.add_relation(Relation(source="a", target="b", type="link"))
        assert engine.connected_component("a") == {"a", "b"}

    def test_relation_between(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        engine.graph.add_relation(Relation(source="a", target="b", type="knows"))
        rels = engine.relation_between("a", "b")
        assert len(rels) == 1
        assert rels[0].type == "knows"

    def test_most_similar(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        engine.graph.add_entity(Entity(id="c", name="C", type="t"))
        engine.graph.add_relation(Relation(source="a", target="b", type="link"))
        engine.graph.add_relation(Relation(source="a", target="c", type="link"))
        top = engine.most_similar("a", top_k=2)
        assert len(top) == 2

    def test_degree(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        engine.graph.add_relation(Relation(source="a", target="b", type="link"))
        assert engine.degree("a") == 1

    def test_central_nodes(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        engine.graph.add_entity(Entity(id="c", name="C", type="t"))
        engine.graph.add_relation(Relation(source="a", target="b", type="link"))
        engine.graph.add_relation(Relation(source="a", target="c", type="link"))
        top = engine.central_nodes(top_k=1)
        assert len(top) == 1
        assert top[0][0] == "a"

    def test_diameter_returns_none_for_disconnected(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        assert engine.diameter() is None

    def test_diameter_connected(self):
        engine = QueryEngine()
        engine.graph.add_entity(Entity(id="a", name="A", type="t"))
        engine.graph.add_entity(Entity(id="b", name="B", type="t"))
        engine.graph.add_relation(Relation(source="a", target="b", type="link"))
        assert engine.diameter() == pytest.approx(1.0)
