"""Tests for the cognitive memory brain."""

from __future__ import annotations

import unittest

from app.executor.memory_brain import (
    EpisodicMemory,
    LongTermMemory,
    MemoryBrain,
    MemoryCompression,
    MemoryItem,
    MemoryType,
    ProceduralMemory,
    SemanticMemory,
    WorkingMemory,
    get_memory_brain,
)


class WorkingMemoryTest(unittest.TestCase):
    def test_capacity(self):
        wm = WorkingMemory(capacity=2)
        wm.add(MemoryItem(id="a", type=MemoryType.WORKING, content="1"))
        wm.add(MemoryItem(id="b", type=MemoryType.WORKING, content="2"))
        wm.add(MemoryItem(id="c", type=MemoryType.WORKING, content="3"))
        items = wm.list()
        self.assertEqual(len(items), 2)
        self.assertEqual({i.id for i in items}, {"b", "c"})

    def test_get_updates_access(self):
        wm = WorkingMemory()
        wm.add(MemoryItem(id="a", type=MemoryType.WORKING, content="1"))
        item = wm.get("a")
        self.assertEqual(item.access_count, 1)


class LongTermMemoryTest(unittest.TestCase):
    def test_search(self):
        ltm = LongTermMemory()
        ltm.add(MemoryItem(id="a", type=MemoryType.LONG_TERM, content="authentication flows"))
        ltm.add(MemoryItem(id="b", type=MemoryType.LONG_TERM, content="database backups"))
        results = ltm.search("authentication")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "a")

    def test_forget(self):
        ltm = LongTermMemory()
        item = MemoryItem(id="a", type=MemoryType.LONG_TERM, content="x", importance=0.0, confidence=0.0)
        ltm.add(item)
        forgotten = ltm.forget(threshold=0.5)
        self.assertIn("a", forgotten)

    def test_consolidate(self):
        ltm = LongTermMemory()
        item = MemoryItem(id="a", type=MemoryType.LONG_TERM, content="x", importance=0.5)
        ltm.add(item)
        item.access_count = 5
        count = ltm.consolidate()
        self.assertGreaterEqual(count, 1)
        self.assertGreater(item.importance, 0.5)


class EpisodicMemoryTest(unittest.TestCase):
    def test_session_filter(self):
        em = EpisodicMemory()
        em.add(MemoryItem(id="a", type=MemoryType.EPISODIC, content="1", session_id="s1"))
        em.add(MemoryItem(id="b", type=MemoryType.EPISODIC, content="2", session_id="s2"))
        s1 = em.by_session("s1")
        self.assertEqual(len(s1), 1)
        self.assertEqual(s1[0].id, "a")


class SemanticMemoryTest(unittest.TestCase):
    def test_higher_confidence_wins(self):
        sm = SemanticMemory()
        sm.upsert(MemoryItem(id="x", type=MemoryType.SEMANTIC, content="low", confidence=0.3))
        sm.upsert(MemoryItem(id="x", type=MemoryType.SEMANTIC, content="high", confidence=0.9))
        self.assertEqual(sm.get("x").content, "high")

    def test_decay(self):
        sm = SemanticMemory()
        sm.upsert(MemoryItem(id="x", type=MemoryType.SEMANTIC, content="x", confidence=1.0))
        sm.decay(rate=0.5)
        self.assertAlmostEqual(sm.get("x").confidence, 0.5, places=4)


class ProceduralMemoryTest(unittest.TestCase):
    def test_search(self):
        pm = ProceduralMemory()
        pm.add(MemoryItem(id="a", type=MemoryType.PROCEDURAL, content="how to deploy", tags=["devops"]))
        results = pm.search("deploy")
        self.assertEqual(len(results), 1)


class MemoryBrainTest(unittest.TestCase):
    def test_remember_recall(self):
        brain = MemoryBrain()
        brain.remember("authentication uses OAuth2", type=MemoryType.LONG_TERM, tags=["auth"])
        brain.remember("database uses postgres", type=MemoryType.LONG_TERM, tags=["db"])
        results = brain.recall("authentication")
        self.assertGreater(len(results), 0)
        self.assertTrue(any("OAuth" in str(r.content) for r in results))

    def test_session_replay(self):
        brain = MemoryBrain()
        brain.remember("login", type=MemoryType.EPISODIC, session_id="s1")
        brain.remember("dashboard", type=MemoryType.EPISODIC, session_id="s1")
        events = brain.replay("s1")
        self.assertEqual(len(events), 2)

    def test_compress(self):
        brain = MemoryBrain()
        brain.remember("step 1", type=MemoryType.EPISODIC, session_id="s1")
        brain.remember("step 2", type=MemoryType.EPISODIC, session_id="s1")
        text = brain.compress_session("s1")
        self.assertIn("step 1", text)
        self.assertIn("step 2", text)

    def test_consolidate(self):
        brain = MemoryBrain()
        item = brain.remember("x", type=MemoryType.LONG_TERM, importance=0.3)
        item.access_count = 5
        stats = brain.consolidate()
        self.assertGreaterEqual(stats["long_term"], 1)

    def test_stats(self):
        brain = MemoryBrain()
        brain.remember("x", type=MemoryType.LONG_TERM)
        brain.remember("y", type=MemoryType.EPISODIC, session_id="s1")
        stats = brain.stats()
        self.assertIn("long_term", stats)
        self.assertIn("episodic", stats)


if __name__ == "__main__":
    unittest.main()