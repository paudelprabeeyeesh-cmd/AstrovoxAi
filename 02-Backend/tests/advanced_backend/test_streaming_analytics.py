import time
import pytest
from advanced_backend.streaming_analytics import EventStream, Event


def test_publish_consume():
    stream = EventStream(retention_seconds=10)
    event = Event(topic="t1", payload={"v": 1})
    stream.publish(event)
    out = stream.consume("t1", timeout=1.0)
    assert out is not None
    assert out.payload["v"] == 1


def test_subscriber_called():
    stream = EventStream()
    received = []
    stream.subscribe("t1", lambda e: received.append(e))
    stream.publish(Event(topic="t1", payload="hello"))
    assert len(received) == 1
    assert received[0].payload == "hello"


def test_analytics_window():
    stream = EventStream(retention_seconds=10)
    for _ in range(5):
        stream.publish(Event(topic="t1", payload=None))
    stats = stream.analytics("t1", window_seconds=60)
    assert stats["events_in_window"] == 5
    assert stats["throughput_per_sec"] == pytest.approx(5 / 60, rel=1e-3)


def test_retention_prune():
    stream = EventStream(retention_seconds=0.1, max_events=100)
    stream.publish(Event(topic="t1", payload=1))
    time.sleep(0.15)
    stream.publish(Event(topic="t1", payload=2))
    out = stream.consume("t1", timeout=1.0)
    assert out.payload == 2
