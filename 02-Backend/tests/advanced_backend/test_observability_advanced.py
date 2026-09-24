from advanced_backend.observability_advanced import ObservableRegistry, observability


def test_record_and_log():
    registry = ObservableRegistry()
    registry.record(__import__("advanced_backend.observability_advanced", fromlist=["MetricSample"]).MetricSample("reqs", 1.0, {"p": "1"}))
    registry.log("info", "hello")
    exported = registry.export()
    assert len(exported["metrics"]) == 1
    assert any(e.get("message") == "hello" or e.get("event") == "metric" for e in exported["logs"])


def test_span_lifecycle():
    registry = ObservableRegistry()
    span = registry.start_span("op")
    assert span.name == "op"
    registry.end_span(span)
    exported = registry.export()
    assert len(exported["spans"]) == 1
    trace = list(exported["spans"].values())[0]
    assert trace[0]["name"] == "op"


def test_global_observability():
    observability.log("warn", "test_warn", user="u1")
    logs = observability.export()["logs"]
    assert any(e["message"] == "test_warn" for e in logs)
