"""Tests for the distributed worker cluster."""

from __future__ import annotations

import time
import unittest

from app.executor.cluster import (
    Worker,
    WorkerRegistry,
    WorkerState,
    get_worker_registry,
    seed_default_workers,
)


class WorkerClusterTest(unittest.TestCase):
    def test_register_and_heartbeat(self):
        registry = WorkerRegistry()
        worker = registry.register(Worker(id="", name="w1"))
        self.assertEqual(worker.state, WorkerState.IDLE)
        self.assertTrue(registry.heartbeat(worker.id))

    def test_pick(self):
        registry = WorkerRegistry()
        registry.register(Worker(id="", name="a", capacity=2))
        registry.register(Worker(id="", name="b", capacity=4))
        picked = registry.pick("b")
        self.assertIsNotNone(picked)
        self.assertEqual(picked.name, "b")

    def test_capacity_filter(self):
        registry = WorkerRegistry()
        w = registry.register(Worker(id="", name="x", capacity=1))
        registry.mark_busy(w.id, "job-1")
        self.assertIsNone(registry.pick("x"))

    def test_dead_worker_detection(self):
        registry = WorkerRegistry()
        w = registry.register(Worker(id="", name="x"))
        w.last_heartbeat = 0
        dead = registry.detect_dead()
        self.assertIn(w.id, dead)

    def test_rebalance(self):
        registry = WorkerRegistry()
        w = registry.register(Worker(id="", name="x"))
        registry.mark_busy(w.id, "job-1")
        w.last_heartbeat = 0
        rebalanced = registry.rebalance()
        self.assertEqual(len(rebalanced), 1)
        self.assertEqual(rebalanced[0]["from_worker"], w.id)
        self.assertEqual(rebalanced[0]["job_id"], "job-1")

    def test_drain_excluded(self):
        registry = WorkerRegistry()
        w = registry.register(Worker(id="", name="x"))
        w.state = WorkerState.DRAINING
        self.assertIsNone(registry.pick("x"))

    def test_load_balancing(self):
        registry = WorkerRegistry()
        w1 = registry.register(Worker(id="", name="a", capacity=4))
        w2 = registry.register(Worker(id="", name="a", capacity=4))
        registry.mark_busy(w1.id, "j1")
        registry.mark_busy(w1.id, "j2")
        registry.mark_busy(w1.id, "j3")
        # w2 should be picked because w1 is loaded.
        picked = registry.pick("a")
        self.assertEqual(picked.id, w2.id)

    def test_status(self):
        registry = WorkerRegistry()
        registry.register(Worker(id="", name="a"))
        registry.register(Worker(id="", name="b"))
        status = registry.status()
        self.assertEqual(status["total"], 2)
        self.assertIn("idle", status["by_state"])

    def test_seed(self):
        seed_default_workers()
        self.assertGreaterEqual(len(get_worker_registry().list()), 2)


if __name__ == "__main__":
    unittest.main()