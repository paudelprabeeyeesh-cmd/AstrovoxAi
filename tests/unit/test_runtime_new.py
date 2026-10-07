"""Tests for runtime thread pool and async scheduler - expanded coverage."""

from __future__ import annotations

import time

import pytest

from astrovox.runtime import AsyncScheduler, ThreadPool


def test_thread_pool_shutdown_without_wait():
    pool = ThreadPool(workers=1)
    pool.submit(lambda: None)
    pool.shutdown(wait=False)


def test_thread_pool_map_executes_all():
    pool = ThreadPool(workers=2)
    results = pool.map(lambda x: x * 2, [1, 2, 3])
    assert results == [2, 4, 6]
    pool.shutdown(wait=True)


def test_async_scheduler_run_multiple():
    pool = ThreadPool(workers=2)
    scheduler = AsyncScheduler(pool=pool)
    events = [scheduler.run(lambda x: x + 1, i) for i in range(5)]
    scheduler.wait_all(events)
    pool.shutdown(wait=True)
    assert all(e.is_set() for e in events)


def test_thread_pool_submit_returns_event():
    pool = ThreadPool(workers=1)
    event = pool.submit(time.sleep, 0.01)
    assert hasattr(event, "is_set")


def test_thread_pool_worker_count():
    pool = ThreadPool(workers=4)
    assert pool.workers == 4
    pool.shutdown(wait=True)
