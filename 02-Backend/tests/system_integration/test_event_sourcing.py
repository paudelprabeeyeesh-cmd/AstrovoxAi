from system_integration.event_sourcing import Event, EventStore, EventProjection


def test_event_to_dict():
    event = Event(aggregate_id="a1", event_type="created", payload={"k": "v"})
    data = event.to_dict()
    assert data["aggregate_id"] == "a1"
    assert data["event_type"] == "created"


def test_append_and_read_stream():
    store = EventStore()
    event = Event(aggregate_id="a1", event_type="created", payload={"k": "v"}, stream="s1")
    store.append(event)
    events = store.read_stream("s1")
    assert len(events) == 1
    assert events[0].aggregate_id == "a1"


def test_read_aggregate():
    store = EventStore()
    store.append(Event(aggregate_id="a1", event_type="t1", payload={}, stream="s1"))
    store.append(Event(aggregate_id="a1", event_type="t2", payload={}, stream="s2"))
    events = store.read_aggregate("a1")
    assert len(events) == 2


def test_subscribe_called():
    store = EventStore()
    hits = []
    store.subscribe(lambda e: hits.append(1))
    store.append(Event(aggregate_id="a1", event_type="t1", payload={}, stream="s1"))
    assert hits == [1]


def test_projection_build():
    store = EventStore()
    store.append(Event(aggregate_id="a1", event_type="t1", payload={"key": "k1", "value": 1}, stream="s1"))
    proj = EventProjection(store)
    state = proj.build("s1", initial={})
    assert state["k1"] == 1


def test_checkpoint():
    store = EventStore()
    store.append(Event(aggregate_id="a1", event_type="t1", payload={}, stream="s1", version=1))
    store.checkpoint("s1", 1)
    assert store._checkpoints["s1"] == 1
