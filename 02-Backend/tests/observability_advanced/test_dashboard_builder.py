from advanced_backend.observability_advanced.dashboard_builder import DashboardBuilder


def test_build_empty():
    builder = DashboardBuilder()
    result = builder.build()
    assert result["metrics_summary"] == {}
    assert result["log_summary"] == {}
    assert result["span_count"] == 0
    assert result["trace_count"] == 0


def test_build_with_metrics():
    builder = DashboardBuilder()
    builder.add_metrics_snapshot({
        "metrics": {
            "cpu": [{"value": 1.0}, {"value": 2.0}],
            "mem": [{"value": 3.0}],
        }
    })
    result = builder.build()
    assert result["metrics_summary"]["cpu"] == 2
    assert result["metrics_summary"]["mem"] == 1


def test_build_with_logs():
    builder = DashboardBuilder()
    builder.add_logs([
        {"level": "info", "message": "a"},
        {"level": "error", "message": "b"},
        {"level": "info", "message": "c"},
    ])
    result = builder.build()
    assert result["log_summary"]["info"] == 2
    assert result["log_summary"]["error"] == 1


def test_build_with_spans():
    builder = DashboardBuilder()
    builder.add_spans({
        "t1": [{"name": "a"}, {"name": "b"}],
        "t2": [{"name": "c"}],
    })
    result = builder.build()
    assert result["span_count"] == 3
    assert result["trace_count"] == 2


def test_add_spans_extends_existing():
    builder = DashboardBuilder()
    builder.add_spans({"t1": [{"name": "a"}]})
    builder.add_spans({"t1": [{"name": "b"}]})
    result = builder.build()
    assert result["span_count"] == 2
    assert result["trace_count"] == 1


def test_build_combined():
    builder = DashboardBuilder()
    builder.add_metrics_snapshot({
        "metrics": {
            "cpu": [{"value": 1.0}],
        }
    })
    builder.add_logs([
        {"level": "info", "message": "ok"},
        {"level": "error", "message": "fail"},
    ])
    builder.add_spans({
        "t1": [{"name": "a"}],
    })
    result = builder.build()
    assert result["metrics_summary"]["cpu"] == 1
    assert result["log_summary"]["info"] == 1
    assert result["log_summary"]["error"] == 1
    assert result["span_count"] == 1
    assert result["trace_count"] == 1


def test_log_default_level():
    builder = DashboardBuilder()
    builder.add_logs([
        {"message": "no level"},
        {"level": "warn", "message": "with level"},
    ])
    result = builder.build()
    assert result["log_summary"]["info"] == 1
    assert result["log_summary"]["warn"] == 1


def test_add_metrics_snapshot_empty():
    builder = DashboardBuilder()
    builder.add_metrics_snapshot({"metrics": {}})
    result = builder.build()
    assert result["metrics_summary"] == {}


def test_add_logs_empty():
    builder = DashboardBuilder()
    builder.add_logs([])
    result = builder.build()
    assert result["log_summary"] == {}


def test_add_spans_empty():
    builder = DashboardBuilder()
    builder.add_spans({})
    result = builder.build()
    assert result["span_count"] == 0
    assert result["trace_count"] == 0
