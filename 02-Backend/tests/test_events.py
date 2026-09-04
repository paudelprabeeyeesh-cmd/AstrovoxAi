"""Tests for the event-sourced architecture."""

from __future__ import annotations

import logging
import time
import unittest
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from app.events.event_store import EventEnvelope, EventSchema, EventSchemaRegistry, EventStore, EventVersion
from app.events.projection import ProjectionDefinition, ProjectionEngine
from app.events.replay import ReplayEngine, ReplayOptions
from app.events.dead_letter import DeadLetterQueue
from app.events.idempotency import IdempotencyTracker
from app.events.multi_region import MultiRegionEventStore, VectorClock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(event_type: str = "TestEvent", payload: Dict[str, Any] = None) -> EventEnvelope:
    """Create a test event."""
    return EventEnvelope(
        event_id=f"evt-{time.time_ns()}",
        event_type=event_type,
        version=EventVersion.V1,
        payload=payload or {"data": "test"},
        occurred_at=datetime.now(timezone.utc),
        source="test",
        correlation_id="corr-1",
        causation_id=None,
        trace_id="trace-1",
        user_id="user-1",
        idempotency_key=f"key-{time.time_ns()}",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class EventSchemaRegistryTest(unittest.TestCase):
    def test_register_and_get_schema(self):
        registry = EventSchemaRegistry()
        schema = EventSchema(
            name="TestEvent",
            version=EventVersion.V1,
            fields={"data": "string"},
        )
        registry.register(schema)

        retrieved = registry.get_schema("TestEvent")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "TestEvent")
        self.assertEqual(retrieved.version, EventVersion.V1)

    def test_get_latest_version(self):
        registry = EventSchemaRegistry()
        registry.register(EventSchema(name="TestEvent", version=EventVersion.V1, fields={"data": "string"}))
        registry.register(EventSchema(name="TestEvent", version=EventVersion.V2, fields={"data": "string", "extra": "int"}))

        latest = registry.get_latest_version("TestEvent")
        self.assertEqual(latest, EventVersion.V2)

    def test_validate_valid_event(self):
        registry = EventSchemaRegistry()
        registry.register(EventSchema(name="TestEvent", version=EventVersion.V1, fields={"data": "string"}))

        event = make_event("TestEvent", {"data": "hello"})
        errors = registry.validate(event)
        self.assertEqual(errors, [])

    def test_validate_missing_field(self):
        registry = EventSchemaRegistry()
        registry.register(EventSchema(name="TestEvent", version=EventVersion.V1, fields={"data": "string"}))

        event = make_event("TestEvent", {"wrong_field": "hello"})
        errors = registry.validate(event)
        self.assertGreater(len(errors), 0)


class EventStoreTest(unittest.TestCase):
    def test_append_and_retrieve(self):
        registry = EventSchemaRegistry()
        registry.register(EventSchema(name="TestEvent", version=EventVersion.V1, fields={}))
        store = EventStore(registry)

        event = make_event("TestEvent")
        stored = store.append(event, idempotency_key=event.idempotency_key)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.event_id, event.event_id)

        retrieved = store.get_events(event_type="TestEvent")
        self.assertEqual(len(retrieved), 1)

    def test_idempotency(self):
        registry = EventSchemaRegistry()
        store = EventStore(registry)

        event = make_event("TestEvent")
        store.append(event, idempotency_key="dup-key")
        store.append(event, idempotency_key="dup-key")  # Should be suppressed

        events = store.get_events(event_type="TestEvent")
        self.assertEqual(len(events), 1)

    def test_snapshot(self):
        registry = EventSchemaRegistry()
        store = EventStore(registry)

        store.snapshot("agg-1", {"state": "value"}, position=10)
        snapshot = store.get_snapshot("agg-1")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["state"], "value")
        self.assertEqual(snapshot["position"], 10)

    def test_replay(self):
        registry = EventSchemaRegistry()
        store = EventStore(registry)
        registry.register(EventSchema(name="TestEvent", version=EventVersion.V1, fields={}))

        for i in range(5):
            event = make_event("TestEvent", {"count": i})
            store.append(event)

        processed = []
        def handler(event):
            processed.append(event.payload["count"])

        count = store.replay(handler, event_type="TestEvent")
        self.assertEqual(count, 5)
        self.assertEqual(len(processed), 5)


class ProjectionEngineTest(unittest.TestCase):
    def test_register_and_process(self):
        registry = EventSchemaRegistry()
        store = EventStore(registry)
        engine = ProjectionEngine(store)

        registry.register(EventSchema(name="CounterIncremented", version=EventVersion.V1, fields={}))

        state = {"count": 0}
        def handler(event, state):
            state["count"] += 1

        engine.register(ProjectionDefinition(
            name="counter",
            event_types=["CounterIncremented"],
            handler=handler,
            initial_state=state,
        ))

        for _ in range(3):
            event = make_event("CounterIncremented")
            store.append(event)

        # Process projection
        engine._process_projection("counter", engine._projections["counter"])

        proj_state = engine.get_projection_state("counter")
        self.assertIsNotNone(proj_state)
        self.assertEqual(proj_state["count"], 3)


class DeadLetterQueueTest(unittest.TestCase):
    def test_enqueue_and_retry(self):
        dlq = DeadLetterQueue()

        event = make_event("TestEvent")
        dlq.enqueue(event, "handler_failed", "connection error")

        self.assertEqual(dlq.size(), 1)

        # First retry should succeed
        retried = dlq.retry(lambda e: None)
        self.assertEqual(retried, 1)
        self.assertEqual(dlq.size(), 0)

    def test_max_retries(self):
        dlq = DeadLetterQueue()
        dlq._queue[0].max_retries = 1  # Will fail after first retry

        event = make_event("TestEvent")
        dlq.enqueue(event, "handler_failed", "connection error")

        def failing_handler(e):
            raise RuntimeError("still failing")

        dlq.retry(failing_handler)
        self.assertEqual(dlq.size(), 1)  # Still in DLQ


class IdempotencyTrackerTest(unittest.TestCase):
    def test_track_and_check(self):
        tracker = IdempotencyTracker(default_ttl_s=3600)

        self.assertFalse(tracker.is_processed("key-1"))
        tracker.record("key-1", "evt-1", "success")
        self.assertTrue(tracker.is_processed("key-1"))
        self.assertEqual(tracker.get_result("key-1"), "success")


class VectorClockTest(unittest.TestCase):
    def test_happens_before(self):
        clock_a = VectorClock(region_id="region-a")
        clock_b = VectorClock(region_id="region-b")

        clock_a.increment()  # a: 1
        clock_b.increment()  # b: 1

        # Neither happens before the other (concurrent)
        self.assertFalse(clock_a.happens_before(clock_b))
        self.assertFalse(clock_b.happens_before(clock_a))

    def test_merge(self):
        clock_a = VectorClock(region_id="region-a")
        clock_b = VectorClock(region_id="region-b")

        clock_a.increment()  # a: 1
        clock_b.increment()  # b: 1
        clock_a.merge(clock_b)

        self.assertEqual(clock_a.timestamps["region-a"], 1)
        self.assertEqual(clock_a.timestamps["region-b"], 1)


if __name__ == "__main__":
    unittest.main()
