"""Tests for the distributed memory system (Stage 37 Program D)."""

from __future__ import annotations

import unittest

from app.acdos.distributed_memory import (
    ConflictResolution,
    EpisodicMemory,
    LongTermMemory,
    MemoryBrain,
    MemoryItem,
    MemoryType,
    ProceduralMemory,
    SemanticIndex,
    SemanticMemory,
    SharedMemory,
    SyncContext,
    WorkingMemory,
    get_memory_brain,
)


class WorkingMemoryTest(unittest.TestCase):
    def test_capacity(self):
        wm = WorkingMemory(capacity=2)
        wm.add(MemoryItem(id="a", type=MemoryType.WORKING, content="1", owner="n1"))
        wm.add(MemoryItem(id="b", type=MemoryType.WORKING, content="2", owner="n1"))
        wm.add(MemoryItem(id="c", type=MemoryType.WORKING, content="3", owner="n1"))
        items = wm.list()
        self.assertEqual(len(items), 2)
        self.assertEqual({i.id for i in items}, {"b", "c"})

    def test_get_updates_access(self):
        wm = WorkingMemory()
        wm.add(MemoryItem(id="a", type=MemoryType.WORKING, content="1", owner="n1"))
        item = wm.get("a")
        self.assertEqual(item.access_count, 1)


class LongTermMemoryTest(unittest.TestCase):
    def test_consolidate(self):
        ltm = LongTermMemory()
        item = MemoryItem(id="a", type=MemoryType.LONG_TERM, content="x", owner="n1", importance=0.5)
        ltm.add(item)
        item.access_count = 5
        count = ltm.consolidate()
        self.assertGreaterEqual(count, 1)
        self.assertGreater(item.importance, 0.5)

    def test_prune(self):
        ltm = LongTermMemory()
        item = MemoryItem(id="a", type=MemoryType.LONG_TERM, content="x", owner="n1", importance=0.0, confidence=0.0)
        ltm.add(item)
        forgotten = ltm.prune(threshold=0.5)
        self.assertEqual(forgotten, 1)


class EpisodicMemoryTest(unittest.TestCase):
    def test_session_filter(self):
        em = EpisodicMemory()
        em.add_event(MemoryItem(id="a", type=MemoryType.EPISODIC, content="1", owner="n1", session_id="s1"))
        em.add_event(MemoryItem(id="b", type=MemoryType.EPISODIC, content="2", owner="n1", session_id="s2"))
        s1 = em.by_session("s1")
        self.assertEqual(len(s1), 1)
        self.assertEqual(s1[0].id, "a")


class SemanticMemoryTest(unittest.TestCase):
    def test_upsert(self):
        sm = SemanticMemory()
        sm.upsert(MemoryItem(id="x", type=MemoryType.SEMANTIC, content="low", owner="n1", confidence=0.3))
        sm.upsert(MemoryItem(id="x", type=MemoryType.SEMANTIC, content="high", owner="n1", confidence=0.9))
        self.assertEqual(sm.get("x").content, "high")

    def test_by_tag(self):
        sm = SemanticMemory()
        sm.upsert(MemoryItem(id="a", type=MemoryType.SEMANTIC, content="x", owner="n1", tags=["tag1"]))
        sm.upsert(MemoryItem(id="b", type=MemoryType.SEMANTIC, content="y", owner="n1", tags=["tag2"]))
        results = sm.by_tag("tag1")
        self.assertEqual(len(results), 1)


class ProceduralMemoryTest(unittest.TestCase):
    def test_match(self):
        pm = ProceduralMemory()
        pm.add_pattern(MemoryItem(id="a", type=MemoryType.PROCEDURAL, content="how to deploy", owner="n1", tags=["devops"]))
        results = pm.match("deploy")
        self.assertEqual(len(results), 1)


class SharedMemoryTest(unittest.TestCase):
    def test_local_write(self):
        sm = SharedMemory("node-1")
        item = sm.local_write(MemoryItem(id="x", type=MemoryType.SHARED, content="data", owner="n1"))
        self.assertEqual(item.vector_clock.get("node-1"), 1)
        self.assertEqual(item.version, 2)

    def test_receive_and_merge(self):
        sm = SharedMemory("node-2")
        # Create local version
        local = MemoryItem(id="x", type=MemoryType.SHARED, content="local", owner="n1", version=2)
        local.vector_clock["node-1"] = 2
        local.vector_clock["node-2"] = 1
        sm._local["x"] = MemoryItem(id="x", type=MemoryType.SHARED, content="local", owner="n1", version=2)
        sm._local["x"].vector_clock["node-1"] = 2

        # Receive remote with higher version
        remote = MemoryItem(id="x", type=MemoryType.SHARED, content="remote", owner="n1", version=3)
        remote.vector_clock["node-1"] = 3

        ctx = sm.receive("node-1", remote)
        self.assertEqual(ctx.resolution, ConflictResolution.LAST_WRITE_WINS)
        self.assertEqual(sm._local["x"].version, 3)

    def test_merge_vector_clocks(self):
        sm = SharedMemory("node-2")
        # Setup local with clock {node-1: 1, node-2: 2}
        local = MemoryItem(id="x", type=MemoryType.SHARED, content="local", owner="n1")
        local.vector_clock = {"node-1": 1, "node-2": 2}
        sm._local["x"] = local

        # Receive remote with clock {node-1: 3, node-2: 1}
        remote = MemoryItem(id="x", type=MemoryType.SHARED, content="remote", owner="n1")
        remote.vector_clock = {"node-1": 3, "node-2": 1}

        ctx = sm.receive("node-1", remote)
        # Merged clock should take max of each
        merged = sm._local["x"].vector_clock
        self.assertEqual(merged["node-1"], 3)
        self.assertEqual(merged["node-2"], 2)


class SemanticIndexTest(unittest.TestCase):
    def test_add_and_search(self):
        idx = SemanticIndex()
        idx.add(MemoryItem(id="a", type=MemoryType.SEMANTIC, content="authentication flow", owner="n1"))
        idx.add(MemoryItem(id="b", type=MemoryType.SEMANTIC, content="database backup", owner="n1"))
        results = idx.search("auth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "a")


class MemoryBrainTest(unittest.TestCase):
    def test_remember_recall(self):
        brain = MemoryBrain()
        brain.remember("auth uses OAuth2", type=MemoryType.LONG_TERM, tags=["auth"])
        brain.remember("database uses postgres", type=MemoryType.LONG_TERM, tags=["db"])
        results = brain.recall("authentication")
        self.assertGreater(len(results), 0)
        self.assertTrue(any("OAuth" in str(r.content) for r in results))

    def test_session_replay(self):
        brain = MemoryBrain()
        brain.remember("login", type=MemoryType.EPISODIC, session_id="s1")
        brain.remember("dashboard", type=MemoryType.EPISODIC, session_id="s1")
        events = brain.episodic.by_session("s1")
        self.assertEqual(len(events), 2)

    def test_compress(self):
        brain = MemoryBrain()
        brain.remember("step 1", type=MemoryType.EPISODIC, session_id="s1")
        brain.remember("step 2", type=MemoryType.EPISODIC, session_id="s1")
        text = brain.episodic.by_session("s1")[0].content
        self.assertIn("step", text)

    def test_consolidate(self):
        brain = MemoryBrain()
        item = brain.remember("x", type=MemoryType.LONG_TERM, importance=0.3)
        item.access_count = 5
        stats = brain.consolidate()
        self.assertGreaterEqual(stats["long_term_consolidated"], 1)

    def test_shared_memory_sync(self):
        brain = MemoryBrain(node_id="node-1")
        # Local write
        item = brain.shared.local_write(MemoryItem(id="x", type=MemoryType.SHARED, content="data", owner="n1"))
        # Receive from remote
        remote = MemoryItem(id="x", type=MemoryType.SHARED, content="remote data", owner="n1", version=2)
        remote.vector_clock["node-2"] = 2
        ctx = brain.shared.receive("node-2", remote)
        self.assertEqual(ctx.resolution, ConflictResolution.LAST_WRITE_WINS)


if __name__ == "__main__":
    unittest.main()