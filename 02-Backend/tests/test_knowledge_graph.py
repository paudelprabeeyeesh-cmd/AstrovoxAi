from knowledge_graph.knowledge_graph import KnowledgeGraph, Entity, Relation


class TestKnowledgeGraph:
    def test_add_and_query(self):
        kg = KnowledgeGraph()
        e1 = Entity(id="e1", name="Alice", type="person")
        e2 = Entity(id="e2", name="Bob", type="person")
        kg.add_entity(e1)
        kg.add_entity(e2)
        assert kg.entities["e1"].name == "Alice"

    def test_add_relation(self):
        kg = KnowledgeGraph()
        kg.add_entity(Entity(id="e1", name="A", type="t"))
        kg.add_entity(Entity(id="e2", name="B", type="t"))
        kg.add_relation(Relation(source="e1", target="e2", type="knows"))
        assert kg.get_neighbors("e1") == [("e2", "knows", 1.0)]

    def test_find_path(self):
        kg = KnowledgeGraph()
        for i in range(4):
            kg.add_entity(Entity(id=f"n{i}", name=f"N{i}", type="node"))
        kg.add_relation(Relation(source="n0", target="n1", type="link"))
        kg.add_relation(Relation(source="n1", target="n2", type="link"))
        kg.add_relation(Relation(source="n2", target="n3", type="link"))
        path = kg.find_path("n0", "n3")
        assert path == ["n0", "n1", "n2", "n3"]

    def test_no_path(self):
        kg = KnowledgeGraph()
        kg.add_entity(Entity(id="a", name="A", type="t"))
        kg.add_entity(Entity(id="b", name="B", type="t"))
        assert kg.find_path("a", "b") is None

    def test_shortest_path_length(self):
        kg = KnowledgeGraph()
        for i in range(3):
            kg.add_entity(Entity(id=f"n{i}", name=f"N{i}", type="node"))
        kg.add_relation(Relation(source="n0", target="n1", type="link"))
        kg.add_relation(Relation(source="n1", target="n2", type="link"))
        assert kg.shortest_path_length("n0", "n2") == 2

    def test_infer_relations(self):
        kg = KnowledgeGraph()
        kg.add_entity(Entity(id="a", name="A", type="t"))
        kg.add_entity(Entity(id="b", name="B", type="t"))
        inferred = kg.infer_relations()
        assert len(inferred) == 1
        assert inferred[0].type == "inferred"

    def test_similarity(self):
        kg = KnowledgeGraph()
        kg.add_entity(Entity(id="a", name="A", type="t"))
        kg.add_entity(Entity(id="b", name="B", type="t"))
        kg.add_entity(Entity(id="c", name="C", type="t"))
        kg.add_relation(Relation(source="a", target="b", type="link"))
        kg.add_relation(Relation(source="a", target="c", type="link"))
        sim = kg.similarity("a", "b")
        assert 0.0 <= sim <= 1.0

    def test_get_subgraph(self):
        kg = KnowledgeGraph()
        for i in range(5):
            kg.add_entity(Entity(id=f"n{i}", name=f"N{i}", type="node"))
        for i in range(4):
            kg.add_relation(Relation(source=f"n{i}", target=f"n{i+1}", type="link"))
        nodes, edges = kg.get_subgraph("n2", depth=1)
        assert "n2" in nodes
        assert "n3" in nodes
        assert "n1" in nodes
