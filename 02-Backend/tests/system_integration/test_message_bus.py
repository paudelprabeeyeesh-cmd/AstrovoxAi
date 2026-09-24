import pytest
from system_integration.message_bus import Message, MessageBus


def make_bus() -> MessageBus:
    bus = MessageBus()
    return bus


def test_publish_deliver():
    bus = MessageBus()
    received = []
    bus.subscribe("t", lambda m: received.append(m.payload))
    bus.publish(Message(topic="t", payload="hello"))
    bus._deliver(Message(topic="t", payload="hello"))
    assert received[-1] == "hello"


def test_subscribe_unsubscribe():
    bus = MessageBus()
    payloads = []
    def handler(m): payloads.append(m.payload)
    bus.subscribe("x", handler)
    bus.unsubscribe("x", handler)
    bus._deliver(Message(topic="x", payload="z"))
    assert payloads == []


def test_last_delivered():
    bus = MessageBus()
    msg = Message(topic="topic", payload=1)
    bus._last_delivered["topic"] = "ts"
    assert bus.last_delivered("topic") == "ts"


def test_priority_queue():
    bus = MessageBus()
    bus.publish(Message(topic="x", payload="low"), priority=0)
    bus.publish(Message(topic="x", payload="high"), priority=10)
    first = bus._queue.pop(0)
    assert first[0].payload == "high"


def test_start_stop():
    bus = MessageBus()
    bus.start()
    assert bus._running is True
    bus.stop()
    assert bus._running is False
