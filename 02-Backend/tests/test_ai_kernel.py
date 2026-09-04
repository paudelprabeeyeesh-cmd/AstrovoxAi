"""Tests for the AI Kernel (Stage 41 Program 1)."""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from app.ai_kernel import (
    AIKernel,
    Actor,
    CheckpointStore,
    EventBus,
    HotReloader,
    KernelState,
    MemoryManager,
    PluginLoader,
    Task,
    TaskPriority,
    TaskScheduler,
    TaskState,
)


async def _ok_task(task: Task) -> str:
    return "ok"


async def _failing_task(task: Task) -> None:
    raise ValueError("nope")


class MemoryManagerTest(unittest.TestCase):
    def test_put_and_get(self):
        m = MemoryManager()
        m.put("k", "v")
        self.assertEqual(m.get("k"), "v")

    def test_ttl(self):
        import time
        m = MemoryManager()
        m.put("k", "v", ttl_seconds=0.0)
        time.sleep(0.05)
        self.assertIsNone(m.get("k"))

    def test_delete(self):
        m = MemoryManager()
        m.put("k", "v")
        self.assertTrue(m.delete("k"))
        self.assertIsNone(m.get("k"))

    def test_keys_with_prefix(self):
        m = MemoryManager()
        m.put("user:1", "alice")
        m.put("user:2", "bob")
        m.put("session:1", "s1")
        self.assertEqual(set(m.keys("user:")), {"user:1", "user:2"})

    def test_snapshot_and_restore(self):
        m = MemoryManager()
        m.put("k1", "v1")
        m.put("k2", "v2")
        snap = m.snapshot()
        m.delete("k1")
        m.restore(snap)
        self.assertEqual(m.get("k1"), "v1")


class EventBusTest(unittest.IsolatedAsyncioTestCase):
    async def test_publish_and_history(self):
        bus = EventBus()
        received: list = []

        async def handler(payload):
            received.append(payload)

        bus.subscribe("test", handler)
        delivered = await bus.publish("test", "hello")
        self.assertEqual(delivered, 1)
        self.assertEqual(received, ["hello"])
        self.assertEqual(len(bus.history()), 1)

    async def test_isolated_handler_failure(self):
        bus = EventBus()
        received: list = []

        async def bad(payload):
            raise RuntimeError("fail")

        async def good(payload):
            received.append(payload)

        bus.subscribe("test", bad)
        bus.subscribe("test", good)
        delivered = await bus.publish("test", "x")
        self.assertEqual(delivered, 1)
        self.assertEqual(received, ["x"])


class TaskSchedulerTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_task(self):
        bus = EventBus()
        memory = MemoryManager()
        scheduler = TaskScheduler(memory=memory, bus=bus)
        task = Task(id="t1", name="t1", handler=_ok_task)
        await scheduler.submit(task)
        finished = await scheduler.run_until_empty()
        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0].state, TaskState.COMPLETED)
        self.assertEqual(finished[0].result, "ok")

    async def test_priority_ordering(self):
        bus = EventBus()
        memory = MemoryManager()
        scheduler = TaskScheduler(memory=memory, bus=bus)
        order: list = []

        async def record(task):
            order.append(task.id)
            return task.id

        await scheduler.submit(Task(id="low", name="low", handler=record, priority=TaskPriority.LOW))
        await scheduler.submit(Task(id="high", name="high", handler=record, priority=TaskPriority.HIGH))
        await scheduler.run_until_empty()
        self.assertEqual(order[0], "high")

    async def test_failure_after_retries(self):
        bus = EventBus()
        memory = MemoryManager()
        scheduler = TaskScheduler(memory=memory, bus=bus)
        task = Task(id="t1", name="t1", handler=_failing_task, max_retries=2)
        await scheduler.submit(task)
        await scheduler.run_until_empty()
        self.assertEqual(task.state, TaskState.FAILED)
        self.assertEqual(task.retries, 2)

    async def test_deadline(self):
        bus = EventBus()
        memory = MemoryManager()
        scheduler = TaskScheduler(memory=memory, bus=bus)
        import time

        async def slow(task):
            await asyncio.sleep(10)
            return "slow"

        task = Task(id="t1", name="t1", handler=slow, deadline=time.time() - 1)
        await scheduler.submit(task)
        finished = await scheduler.run_until_empty()
        self.assertEqual(finished, [])

    async def test_publishes_events(self):
        bus = EventBus()
        memory = MemoryManager()
        scheduler = TaskScheduler(memory=memory, bus=bus)
        completed_events: list = []
        failed_events: list = []

        async def on_completed(payload):
            completed_events.append(payload)

        async def on_failed(payload):
            failed_events.append(payload)

        bus.subscribe("task.completed", on_completed)
        bus.subscribe("task.failed", on_failed)

        task_ok = Task(id="ok", name="ok", handler=_ok_task)
        task_fail = Task(id="fail", name="fail", handler=_failing_task)
        await scheduler.submit(task_ok)
        await scheduler.submit(task_fail)
        await scheduler.run_until_empty()
        self.assertGreater(len(completed_events), 0)
        self.assertGreater(len(failed_events), 0)


class PluginLoaderTest(unittest.TestCase):
    def test_load_and_get(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            plugin_path = Path(tmp) / "hello.py"
            plugin_path.write_text(
                "class Plugin:\n"
                "    def __init__(self):\n"
                "        self.message = 'hello'\n"
            )
            loader = PluginLoader(plugin_dir=tmp)
            record = loader.load("hello")
            self.assertIsNotNone(record.instance)
            self.assertEqual(record.instance.message, "hello")

    def test_load_missing_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            loader = PluginLoader(plugin_dir=tmp)
            with self.assertRaises(FileNotFoundError):
                loader.load("nope")


class HotReloaderTest(unittest.TestCase):
    def test_reload_changed(self):
        import tempfile
        import time as _time

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watched.py"
            path.write_text("class Plugin:\n    value = 1\n")
            loader = PluginLoader(plugin_dir=tmp)
            loader.load("watched")
            reloader = HotReloader(loader)
            # Modify the file
            _time.sleep(0.1)
            path.write_text("class Plugin:\n    value = 2\n")
            reloaded = reloader.reload_changed()
            self.assertIn("watched", reloaded)
            self.assertEqual(loader.get("watched").instance.value, 2)


class CheckpointStoreTest(unittest.TestCase):
    def test_save_and_retrieve(self):
        store = CheckpointStore()
        cp = store.save({"a": 1, "b": 2})
        self.assertEqual(cp.state["a"], 1)
        latest = store.latest()
        self.assertEqual(latest.id, cp.id)
        self.assertIsNotNone(store.get(cp.id))

    def test_max_checkpoints(self):
        store = CheckpointStore(max_checkpoints=2)
        store.save({"v": 1})
        store.save({"v": 2})
        store.save({"v": 3})
        self.assertEqual(len(store.list()), 2)


class AIKernelTest(unittest.IsolatedAsyncioTestCase):
    async def test_lifecycle(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            kernel = AIKernel(plugin_dir=tmp)
            self.assertEqual(kernel.state, KernelState.BOOTING)
            kernel.boot()
            self.assertEqual(kernel.state, KernelState.READY)
            kernel.shutdown()
            self.assertEqual(kernel.state, KernelState.SHUTTING_DOWN)

    async def test_actor_messaging(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            kernel = AIKernel(plugin_dir=tmp)
            received: list = []

            async def handler(msg):
                received.append(msg)

            actor = Actor("test_actor", handler)
            kernel.register_actor(actor)
            await asyncio.sleep(0.05)  # let actor start
            self.assertTrue(await kernel.send_to_actor("test_actor", "hi"))
            await asyncio.sleep(0.1)
            self.assertEqual(received, ["hi"])
            await actor.stop()

    async def test_checkpoint_and_restore(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            kernel = AIKernel(plugin_dir=tmp)
            kernel.memory.put("k1", "v1")
            cp = kernel.checkpoint()
            kernel.memory.delete("k1")
            self.assertIsNone(kernel.memory.get("k1"))
            self.assertTrue(kernel.restore(cp.id))
            self.assertEqual(kernel.memory.get("k1"), "v1")

    def test_status(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            kernel = AIKernel(plugin_dir=tmp)
            kernel.boot()
            status = kernel.status()
            self.assertEqual(status["state"], "ready")
            self.assertIn("memory_version", status)
            self.assertIn("scheduler", status)


if __name__ == "__main__":
    unittest.main()
