"""Tests for the reliability engineering module."""

from __future__ import annotations

import asyncio
import unittest

from app.executor.reliability import (
    Backup,
    ChaosSuite,
    FaultEvent,
    FaultInjector,
    FaultType,
    RecoveryEngine,
    get_chaos_suite,
)


class FaultInjectorTest(unittest.TestCase):
    def test_inject_error(self):
        injector = FaultInjector()
        injector.inject("svc", FaultType.ERROR, message="boom")
        async def run():
            with __import__("contextlib").suppress(RuntimeError):
                await injector.run("svc", lambda: asyncio.sleep(0))
        asyncio.run(run())
        self.assertEqual(len(injector.history()), 1)

    def test_inject_latency(self):
        injector = FaultInjector()
        injector.inject("svc", FaultType.LATENCY, latency_ms=20)

        import time
        async def run():
            await injector.run("svc", lambda: asyncio.sleep(0))

        start = time.time()
        asyncio.run(run())
        self.assertGreaterEqual(time.time() - start, 0.01)

    def test_clear(self):
        injector = FaultInjector()
        injector.inject("svc", FaultType.ERROR)
        injector.clear("svc")
        async def run():
            await injector.run("svc", lambda: asyncio.sleep(0))
        asyncio.run(run())
        self.assertEqual(len(injector.history()), 0)


class RecoveryEngineTest(unittest.TestCase):
    def test_recover(self):
        engine = RecoveryEngine()
        calls = []

        async def handler():
            calls.append(1)

        engine.register("svc", handler)
        ok = asyncio.run(engine.recover("svc"))
        self.assertTrue(ok)
        self.assertEqual(len(calls), 1)

    def test_recover_failure(self):
        engine = RecoveryEngine()

        async def handler():
            raise RuntimeError("recover failed")

        engine.register("svc", handler)
        ok = asyncio.run(engine.recover("svc"))
        self.assertFalse(ok)


class BackupTest(unittest.TestCase):
    def test_create_and_restore(self):
        backup = Backup()
        sid = backup.create("db", {"users": 100})
        self.assertEqual(backup.restore(sid), {"users": 100})

    def test_verify(self):
        backup = Backup()
        sid = backup.create("db", {"a": 1})
        self.assertTrue(backup.verify(sid))

    def test_list(self):
        backup = Backup()
        backup.create("db", {"a": 1})
        items = backup.list()
        self.assertEqual(len(items), 1)


class ChaosSuiteTest(unittest.TestCase):
    def test_experiment(self):
        suite = ChaosSuite()
        result = asyncio.run(
            suite.experiment("test1", "svc", FaultType.ERROR)
        )
        self.assertFalse(result["survived"])
        self.assertEqual(len(suite.results()), 1)


if __name__ == "__main__":
    unittest.main()