import pytest
from knowledge_graph.graph_store import GraphStore
from knowledge_graph.knowledge_graph import Entity, Relation


class TestGraphStore:
    def test_add_entity(self):
        store = GraphStore()
        store.add_entity(Entity(id="e1", name="Alice", type="person"))
        assert store.get_entity("e1").name == "Alice"

    def test_add_relation(self):
        store = GraphStore()
        store.add_entity(Entity(id="e1", name="A", type="t"))
        store.add_entity(Entity(id="e2", name="B", type="t"))
        store.add_relation(Relation(source="e1", target="e2", type="knows"))
        assert store.relation_count() == 1

    def test_remove_entity(self):
        store = GraphStore()
        store.add_entity(Entity(id="e1", name="A", type="t"))
        store.add_entity(Entity(id="e2", name="B", type="t"))
        store.add_relation(Relation(source="e1", target="e2", type="knows"))
        store.remove_entity("e1")
        assert store.entity_count() == 1
        assert store.relation_count() == 0

    def test_list_entities(self):
        store = GraphStore()
        store.add_entity(Entity(id="e1", name="A", type="t"))
        store.add_entity(Entity(id="e2", name="B", type="t"))
        assert len(store.list_entities()) == 2

    def test_merge(self):
        store1 = GraphStore()
        store1.add_entity(Entity(id="e1", name="A", type="t"))
        store2 = GraphStore()
        store2.add_entity(Entity(id="e2", name="B", type="t"))
        store1.merge(store2)
        assert store1.entity_count() == 2

    def test_snapshot(self):
        store = GraphStore()
        store.snapshot("v1")
        assert "v1" in store.snapshot_index
