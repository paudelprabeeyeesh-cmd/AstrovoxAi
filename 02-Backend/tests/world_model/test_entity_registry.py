import unittest

from world_model.entity_registry import Entity, EntityRegistry


class TestEntityRegistry(unittest.TestCase):
    def test_register_and_get(self):
        registry = EntityRegistry()
        registry.register("e1", "agent", {"health": 100.0})
        entity = registry.get("e1")
        self.assertIsNotNone(entity)
        self.assertEqual(entity.id, "e1")
        self.assertEqual(entity.type, "agent")
        self.assertEqual(entity.properties, {"health": 100.0})

    def test_register_duplicate_raises(self):
        registry = EntityRegistry()
        registry.register("e1", "agent")
        with self.assertRaises(ValueError):
            registry.register("e1", "agent")

    def test_unregister(self):
        registry = EntityRegistry()
        registry.register("e1", "agent")
        registry.unregister("e1")
        self.assertIsNone(registry.get("e1"))

    def test_query_by_type(self):
        registry = EntityRegistry()
        registry.register("e1", "agent", {"health": 100.0})
        registry.register("e2", "item", {"value": 10.0})
        agents = registry.query_by_type("agent")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0].id, "e1")

    def test_query_by_property(self):
        registry = EntityRegistry()
        registry.register("e1", "agent", {"team": "red"})
        registry.register("e2", "agent", {"team": "blue"})
        registry.register("e3", "item", {"team": "red"})
        results = registry.query_by_property("team", "red")
        self.assertEqual(len(results), 2)
        ids = {e.id for e in results}
        self.assertEqual(ids, {"e1", "e3"})

    def test_list_all(self):
        registry = EntityRegistry()
        registry.register("e1", "agent")
        registry.register("e2", "item")
        all_entities = registry.list_all()
        self.assertEqual(len(all_entities), 2)

    def test_clear(self):
        registry = EntityRegistry()
        registry.register("e1", "agent")
        registry.clear()
        self.assertEqual(registry.list_all(), [])


if __name__ == "__main__":
    unittest.main()
