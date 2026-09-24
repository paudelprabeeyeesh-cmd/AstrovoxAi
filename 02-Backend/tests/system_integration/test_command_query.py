import pytest
from system_integration.command_query import (
    Command,
    CommandBus,
    CommandResult,
    CommandStatus,
    Query,
    QueryBus,
    QueryResult,
    QueryStatus,
    ReadModel,
    EventualConsistencySync,
)


def test_command_bus_dispatches():
    bus = CommandBus()
    def handler(cmd: Command) -> dict:
        return {"status": "ok"}
    bus.register("do", handler)
    cmd = Command(name="do", payload={"command_id": "c1"})
    result = bus.dispatch(cmd)
    assert result.status == CommandStatus.COMPLETED


def test_command_bus_missing_handler():
    bus = CommandBus()
    cmd = Command(name="missing", payload={"command_id": "c1"})
    result = bus.dispatch(cmd)
    assert result.status == CommandStatus.FAILED
    assert "handler not found" in result.error


def test_query_bus_cache_hit():
    bus = QueryBus()
    def handler(q: Query) -> dict:
        return {"v": 1}
    bus.register("get", handler)
    q = Query(name="get", params={"query_id": "q1"})
    r1 = bus.ask(q)
    r2 = bus.ask(q)
    assert r1.value == {"v": 1}
    assert r2.value == {"v": 1}


def test_read_model_apply():
    m = ReadModel(name="m")
    m.apply({"key": "k1", "value": 10})
    assert m.projection["k1"] == 10


def test_eventual_consistency_sync():
    m = ReadModel(name="m")
    sync = EventualConsistencySync(m)
    sync.enqueue({"key": "k1", "value": 1})
    sync.apply_pending()
    assert m.projection["k1"] == 1


def test_command_history():
    bus = CommandBus()
    bus.register("x", lambda c: {})
    bus.dispatch(Command(name="x", payload={"command_id": "c1"}))
    assert len(bus.history()) == 1


def test_query_history():
    bus = QueryBus()
    bus.register("x", lambda q: {})
    bus.ask(Query(name="x", params={"query_id": "q1"}))
    assert len(bus.history()) == 1
