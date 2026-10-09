import time

from lifelong_learning.memory_consolidator import Memory, MemoryConsolidator


class TestMemoryConsolidator:
    def test_add_memory(self):
        mc = MemoryConsolidator()
        memory = mc.add("m1", "hello")
        assert memory.memory_id == "m1"
        assert memory.content == "hello"
        assert memory.strength == 1.0

    def test_add_duplicate_updates_content(self):
        mc = MemoryConsolidator()
        mc.add("m1", "hello")
        memory = mc.add("m1", "world")
        assert memory.content == "world"
        assert memory.access_count == 1

    def test_consolidate_decays_strength(self):
        mc = MemoryConsolidator(decay_rate=1.0)
        mc.add("m1", "hello")
        time.sleep(0.01)
        log = mc.consolidate()
        assert log["consolidated_count"] == 1
        assert mc.get_memory("m1").strength < 1.0

    def test_consolidate_forgets_weak(self):
        mc = MemoryConsolidator(decay_rate=100.0)
        mc.add("m1", "hello")
        time.sleep(0.01)
        log = mc.consolidate()
        assert log["forgotten_count"] == 1
        assert mc.get_memory("m1") is None

    def test_replay_returns_strongest(self):
        mc = MemoryConsolidator()
        mc.add("m1", "weak").strength = 0.1
        mc.add("m2", "strong").strength = 0.9
        top = mc.replay(k=1)
        assert len(top) == 1
        assert top[0].memory_id == "m2"

    def test_get_stats(self):
        mc = MemoryConsolidator()
        mc.add("m1", "hello")
        mc.add("m2", "world")
        stats = mc.get_stats()
        assert stats["total_memories"] == 2
        assert stats["average_strength"] == 1.0
        assert stats["consolidation_runs"] == 0

    def test_max_memories_forgets_weakest(self):
        mc = MemoryConsolidator(max_memories=2)
        mc.add("m1", "a").strength = 0.5
        mc.add("m2", "b").strength = 0.9
        mc.add("m3", "c").strength = 0.7
        assert len(mc._memories) == 2
        assert "m1" not in mc._memories
