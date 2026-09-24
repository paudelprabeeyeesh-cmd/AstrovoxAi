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
