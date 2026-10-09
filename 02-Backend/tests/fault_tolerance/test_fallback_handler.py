import pytest
from app.fault_tolerance.fallback_handler import FallbackHandler


def test_fallback_used_on_exception():
    primary = lambda: (_ for _ in ()).throw(RuntimeError("fail"))
    fallback = lambda: "fallback"
    handler = FallbackHandler(primary, fallback)
    assert handler.execute() == "fallback"
    assert handler.fallback_count == 1


def test_primary_success():
    handler = FallbackHandler(lambda: "ok", lambda: "fallback")
    assert handler.execute() == "ok"
    assert handler.fallback_count == 0


def test_add_fallback():
    handler = FallbackHandler(lambda: (_ for _ in ()).throw(RuntimeError("fail")), lambda: "first")
    assert handler.execute() == "first"
    handler.add_fallback(lambda: "second")
    assert handler.execute() == "second"
    assert handler.fallback_count == 2


def test_fallback_execute_with_args():
    handler = FallbackHandler(lambda: (_ for _ in ()).throw(RuntimeError("fail")), lambda x, y: x + y)
    assert handler.execute(2, y=3) == 5


def test_fallback_exception_propagates():
    handler = FallbackHandler(lambda: (_ for _ in ()).throw(RuntimeError("fail")), lambda: (_ for _ in ()).throw(ValueError("fallback down")))
    with pytest.raises(ValueError, match="fallback down"):
        handler.execute()


def test_fallback_count_increments_only_on_primary_failure():
    handler = FallbackHandler(lambda: "ok", lambda: "fallback")
    for _ in range(5):
        handler.execute()
    assert handler.fallback_count == 0


def test_multiple_failures_increment_fallback_count():
    handler = FallbackHandler(lambda: (_ for _ in ()).throw(RuntimeError("fail")), lambda: "fallback")
    assert handler.execute() == "fallback"
    assert handler.execute() == "fallback"
    assert handler.fallback_count == 2


def test_primary_exception_type_preserved():
    handler = FallbackHandler(lambda: (_ for _ in ()).throw(ValueError("primary")), lambda: "fallback")
    assert handler.execute() == "fallback"
