"""Tests for jobs, events, caching, and circuit breakers."""

import pytest
import asyncio

from app.jobs import JobQueue, Job, JobStatus, JobPriority, job_queue
from app.events import EventBus, event_bus
from app.caching import CacheLayer, CircuitBreaker, CircuitState, get_circuit_breaker


# ============================================================================
# Job Queue Tests
# ============================================================================

class TestJobQueue:
    def setup_method(self):
        self.queue = JobQueue(max_workers=2)

    @pytest.mark.asyncio
    async def test_submit_job(self):
        await self.queue.submit("test", {"key": "value"})
        assert self.queue.get_stats()["submitted"] == 1

    @pytest.mark.asyncio
    async def test_job_lifecycle(self):
        async def handler(job):
            return {"result": "ok"}

        self.queue.register_handler("test", handler)
        job_id = await self.queue.submit("test", {"key": "value"})

        await self.queue.start()
        await asyncio.sleep(0.5)
        await self.queue.stop()

        job = self.queue.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_job_retry(self):
        call_count = 0

        async def failing_handler(job):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Temporary failure")

        self.queue.register_handler("failing", failing_handler)
        job_id = await self.queue.submit("failing", {}, max_retries=2)

        await self.queue.start()
        await asyncio.sleep(3)
        await self.queue.stop()

        job = self.queue.get_job(job_id)
        assert job.status == JobStatus.DEAD_LETTER
        assert job.retry_count == 2

    @pytest.mark.asyncio
    async def test_cancel_job(self):
        job_id = await self.queue.submit("test", {})
        assert await self.queue.cancel(job_id) is True
        job = self.queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLED


# ============================================================================
# Event Bus Tests
# ============================================================================

class TestEventBus:
    def setup_method(self):
        self.bus = EventBus()

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        received = []

        def handler(event):
            received.append(event.data)

        self.bus.subscribe("test_event", handler)
        await self.bus.publish("test_event", {"key": "value"})

        assert len(received) == 1
        assert received[0] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        count = 0

        def handler1(event):
            nonlocal count
            count += 1

        def handler2(event):
            nonlocal count
            count += 1

        self.bus.subscribe("event", handler1)
        self.bus.subscribe("event", handler2)
        await self.bus.publish("event", {})

        assert count == 2

    @pytest.mark.asyncio
    async def test_event_log(self):
        await self.bus.publish("test", {"a": 1})
        await self.bus.publish("test", {"b": 2})
        await self.bus.publish("other", {"c": 3})

        events = self.bus.get_events(event_type="test")
        assert len(events) == 2


# ============================================================================
# Cache Tests
# ============================================================================

class TestCacheLayer:
    def test_set_and_get(self):
        cache = CacheLayer(default_ttl=60)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_expiration(self):
        cache = CacheLayer(default_ttl=0)
        cache.set("key", "value")
        import time
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_delete(self):
        cache = CacheLayer()
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_stats(self):
        cache = CacheLayer()
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_recovery(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        # With recovery_timeout=0, state should transition to HALF_OPEN on next check
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_get_circuit_breaker(self):
        cb1 = get_circuit_breaker("provider1")
        cb2 = get_circuit_breaker("provider1")
        assert cb1 is cb2
