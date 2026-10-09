import pytest

from advanced_backend.streaming_analytics import Event, EventStream


def test_publish_and_consume() -> None:
    stream = EventStream(retention_seconds=10.0, max_events=100)
    received: list = []

    def handler(event: Event) -> None:
        received.append(event.payload)

    stream.subscribe("orders", handler)
    stream.publish(Event(topic="orders", payload={"id": 1}))
    event = stream.consume("orders", timeout=1.0)
    assert event is not None
    assert event.payload == {"id": 1}
    assert received == [{"id": 1}]


def test_consume_timeout_returns_none() -> None:
    stream = EventStream()
    assert stream.consume("empty", timeout=0.1) is None


def test_analytics_window() -> None:
    stream = EventStream()
    for i in range(5):
        stream.publish(Event(topic="metrics", payload=i))
    stats = stream.analytics("metrics", window_seconds=60.0)
    assert stats["events_in_window"] == 5
    assert stats["topic_distribution"]["metrics"] == 5
    assert stats["throughput_per_sec"] > 0


def test_retention_prunes_old_events() -> None:
    stream = EventStream(retention_seconds=0.0, max_events=100)
    stream.publish(Event(topic="t", payload=1))
    import time

    time.sleep(0.05)
    stream.publish(Event(topic="t", payload=2))
    assert len(stream._events["t"]) == 1


def test_max_events_prunes() -> None:
    stream = EventStream(retention_seconds=3600.0, max_events=2)
    stream.publish(Event(topic="t", payload=1))
    stream.publish(Event(topic="t", payload=2))
    stream.publish(Event(topic="t", payload=3))
    assert len(stream._events["t"]) == 2
