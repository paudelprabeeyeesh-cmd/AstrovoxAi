import pytest
from final_system.system_bus import Message, SystemBus


def test_publish_and_deliver():
    bus = SystemBus()
    received = []
    bus.subscribe("events", lambda m: received.append(m.payload))
    bus.publish(Message(topic="events", payload="hello"))
    assert received == ["hello"]


def test_wildcard_subscription():
    bus = SystemBus()
    received = []
    bus.subscribe("app.*", lambda m: received.append(m.payload))
    bus.publish(Message(topic="app.start", payload="up"))
    assert received == ["up"]


def test_unsubscribe():
    bus = SystemBus()
    received = []
    def handler(m): received.append(m.payload)
    bus.subscribe("events", handler)
    bus.unsubscribe("events", handler)
    bus.publish(Message(topic="events", payload="lost"))
    assert received == []


def test_history():
    bus = SystemBus()
    bus.publish(Message(topic="t", payload=1))
    bus.publish(Message(topic="t", payload=2))
    hist = bus.history("t")
    assert len(hist) == 2
    assert [h.payload for h in hist] == [1, 2]


def test_last_delivered():
    bus = SystemBus()
    bus.publish(Message(topic="t", payload=1))
    assert bus.last_delivered("t") is not None


def test_start_stop():
    bus = SystemBus()
    bus.start()
    assert bus._running is True
    bus.stop()
    assert bus._running is False
