"""Tests for the AI compute fabric."""

from __future__ import annotations

import unittest

from app.acdos.compute_fabric import (
    AIComputeFabric,
    Job,
    JobState,
    Priority,
    PriorityQueue,
    get_compute_fabric,
)
from app.acdos.control_plane import ClusterCoordinator, Node


async def _ok(job):
    return {"ok": True, "job": job.name}


async def _fail(job):
    raise RuntimeError("boom")


class ComputeFabricAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.acdos import control_plane as cp
        from app.acdos import compute_fabric as cf
        cp._GLOBAL_COORDINATOR = None
        cf._GLOBAL_FABRIC = None
        self.coord = ClusterCoordinator()
        self.coord.add_node(Node(id="n1", address="a", capacity={"cpu": 8.0, "gpu": 2.0}))
        self.fabric = AIComputeFabric(coordinator=self.coord)

    async def test_submit_and_run(self):
        self.fabric.submit("job1", _ok, requirements={"cpu": 1.0})
        result = await self.fabric.run(deadline_s=2.0)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["completed"]), 1)

    async def test_retry(self):
        attempts = {"n": 0}

        async def flaky(job):
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise RuntimeError("fail")
            return {"ok": True}

        self.fabric.submit("job", flaky, max_retries=2, requirements={"cpu": 0.5})
        await self.fabric.run(deadline_s=3.0)
        self.assertEqual(attempts["n"], 2)

    async def test_failure(self):
        self.fabric.submit("job", _fail, max_retries=0, requirements={"cpu": 0.5})
        result = await self.fabric.run(deadline_s=2.0)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["failed"]), 1)

    async def test_multi_tenant(self):
        self.fabric.submit("a", _ok, tenant="t1", requirements={"cpu": 0.5})
        self.fabric.submit("b", _ok, tenant="t2", requirements={"cpu": 0.5})
        await self.fabric.run(deadline_s=2.0)
        status = self.fabric.status()
        self.assertIn("t1", status["jobs_by_tenant"])
        self.assertIn("t2", status["jobs_by_tenant"])

    async def test_checkpoints(self):
        job = self.fabric.submit("job", _ok, requirements={"cpu": 0.5})
        await self.fabric.run(deadline_s=1.0)
        cp = self.fabric.checkpoint_job(job.id)
        self.assertIsNotNone(cp)


class PriorityQueueTest(unittest.TestCase):
    def test_priority_ordering(self):
        queue = PriorityQueue()
        low = Job(id="l", name="low", tenant="t", handler=_ok, priority=Priority.LOW)
        high = Job(id="h", name="high", tenant="t", handler=_ok, priority=Priority.HIGH)
        queue.push(low)
        queue.push(high)
        first = queue.pop()
        self.assertEqual(first.id, "h")

    def test_stats(self):
        queue = PriorityQueue()
        queue.push(Job(id="a", name="a", tenant="t", handler=_ok))
        stats = queue.stats()
        self.assertEqual(stats["tracked"], 1)


class ComputeFabricSyncTest(unittest.TestCase):
    def setUp(self):
        from app.acdos import control_plane as cp
        cp._GLOBAL_COORDINATOR = None
        self.coord = ClusterCoordinator()
        self.coord.add_node(Node(id="n1", address="a", capacity={"cpu": 8.0}))
        self.fabric = AIComputeFabric(coordinator=self.coord)

    def test_migration(self):
        job = self.fabric.submit("job", _ok, requirements={"cpu": 0.5})
        self.fabric._jobs[job.id].assigned_node = "n1"
        self.fabric.checkpoint_job(job.id)
        ok = self.fabric.migrate(job.id, target_node="n1")
        self.assertTrue(ok)

    def test_cancel(self):
        job = self.fabric.submit("job", _ok, requirements={"cpu": 0.5})
        self.fabric.cancel(job.id)
        self.assertEqual(self.fabric._jobs[job.id].state, JobState.CANCELLED)

    def test_status(self):
        status = self.fabric.status()
        self.assertIn("queue", status)
        self.assertIn("total_jobs", status)


if __name__ == "__main__":
    unittest.main()