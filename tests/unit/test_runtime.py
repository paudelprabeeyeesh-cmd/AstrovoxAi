"""Tests for runtime thread pool and async scheduler."""

from __future__ import annotations

import threading
import time

import pytest

from astrovox.runtime import AsyncScheduler, ThreadPool


def test_thread_pool_executes_tasks():
    pool = ThreadPool(workers=2)
    results = []
    def work(item):
        results.append(item)
    pool.submit(work, 1)
    pool.submit(work, 2)
    time.sleep(0.1)
    pool.shutdown(wait=True)
    assert len(results) == 2


def test_async_scheduler_waits_for_events():
    pool = ThreadPool(workers=1)
    scheduler = AsyncScheduler(pool=pool)
    events = [scheduler.run(lambda x: x * 2, i) for i in range(3)]
    scheduler.wait_all(events)
    pool.shutdown(wait=True)
    assert all(event.is_set() for event in events)
