import importlib.util
import os
import sys
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_metrics_spec = importlib.util.spec_from_file_location(
    "models.llm.observability.metrics", os.path.join(ROOT, "models", "llm", "observability", "metrics.py")
)
_metrics_mod = importlib.util.module_from_spec(_metrics_spec)
_metrics_spec.loader.exec_module(_metrics_mod)

_alerts_spec = importlib.util.spec_from_file_location(
    "models.llm.observability.alerts", os.path.join(ROOT, "models", "llm", "observability", "alerts.py")
)
_alerts_mod = importlib.util.module_from_spec(_alerts_spec)
_alerts_spec.loader.exec_module(_alerts_mod)

_dashboard_spec = importlib.util.spec_from_file_location(
    "models.llm.observability.dashboard", os.path.join(ROOT, "models", "llm", "observability", "dashboard.py")
)
_dashboard_mod = importlib.util.module_from_spec(_dashboard_spec)
_dashboard_spec.loader.exec_module(_dashboard_mod)

MetricsCollector = _metrics_mod.MetricsCollector
TimeSeriesStore = _metrics_mod.TimeSeriesStore
TimeSeriesPoint = _metrics_mod.TimeSeriesPoint
AlertRule = _alerts_mod.AlertRule
AlertManager = _alerts_mod.AlertManager
AlertRouter = _alerts_mod.AlertRouter
EscalationPolicy = _alerts_mod.EscalationPolicy
router = _dashboard_mod.router


class TestTimeSeriesStore:
    def test_append_and_query(self):
        store = TimeSeriesStore()
        store.append("cpu", 42.0)
        points = store.query("cpu")
        assert len(points) == 1
        assert points[0].value == 42.0

    def test_query_with_time_filter(self):
        store = TimeSeriesStore()
        store.append("cpu", 10.0)
        time.sleep(0.01)
        cutoff = time.time()
        time.sleep(0.01)
        store.append("cpu", 20.0)
        points = store.query("cpu", since=cutoff)
        assert len(points) == 1
        assert points[0].value == 20.0

    def test_aggregate(self):
        store = TimeSeriesStore()
        store.append("cpu", 10.0)
        store.append("cpu", 20.0)
        store.append("cpu", 30.0)
        assert store.aggregate("cpu", max) == 30.0
        assert store.aggregate("cpu", min) == 10.0
        assert store.aggregate("cpu", sum) == 60.0

    def test_clear(self):
        store = TimeSeriesStore()
        store.append("cpu", 10.0)
        store.clear()
        assert len(store.query("cpu")) == 0


class TestMetricsCollector:
    def test_increment_counter(self):
        collector = MetricsCollector()
        collector.increment("requests")
        collector.increment("requests", 2.0)
        assert collector.get_counter("requests") == 3.0

    def test_set_gauge(self):
        collector = MetricsCollector()
        collector.set_gauge("memory", 512.0)
        assert collector.get_gauge("memory") == 512.0

    def test_histogram(self):
        collector = MetricsCollector()
        collector.histogram("latency", 0.1)
        points = collector.store.get("latency_bucket")
        assert len(points) == 1
        assert points[0].value == 0.1

    def test_record(self):
        collector = MetricsCollector()
        collector.record("temp", 65.0)
        assert collector.get_latest("temp") == 65.0

    def test_labels_isolation(self):
        collector = MetricsCollector()
        collector.record("metric", 1.0, {"region": "us"})
        collector.record("metric", 2.0, {"region": "eu"})
        us_points = collector.store.get("metric", {"region": "us"})
        eu_points = collector.store.get("metric", {"region": "eu"})
        assert len(us_points) == 1
        assert len(eu_points) == 1
        assert us_points[0].value == 1.0
        assert eu_points[0].value == 2.0


class TestAlertRule:
    def test_evaluate_true(self):
        rule = AlertRule(name="high_cpu", metric_name="cpu", condition=lambda v: v > 80)
        assert rule.evaluate(90.0) is True

    def test_evaluate_false(self):
        rule = AlertRule(name="high_cpu", metric_name="cpu", condition=lambda v: v > 80)
        assert rule.evaluate(10.0) is False

    def test_cooldown(self):
        rule = AlertRule(name="high_cpu", metric_name="cpu", condition=lambda v: v > 80, cooldown_seconds=60)
        manager = AlertManager()
        manager.add_rule(rule)
        fired1 = manager.evaluate("cpu", 90.0)
        assert len(fired1) == 1
        fired2 = manager.evaluate("cpu", 90.0)
        assert len(fired2) == 0


class TestAlertManager:
    def test_evaluate_and_fire(self):
        rule = AlertRule(name="high_cpu", metric_name="cpu", condition=lambda v: v > 80)
        manager = AlertManager()
        manager.add_rule(rule)
        alerts = manager.evaluate("cpu", 90.0)
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_cpu"

    def test_acknowledge_and_resolve(self):
        rule = AlertRule(name="high_cpu", metric_name="cpu", condition=lambda v: v > 80)
        manager = AlertManager()
        manager.add_rule(rule)
        manager.evaluate("cpu", 90.0)
        manager.acknowledge("high_cpu")
        assert manager.get_active()[0].acknowledged is True
        manager.resolve("high_cpu")
        assert len(manager.get_active()) == 0

    def test_history_limit(self):
        rule = AlertRule(name="high_cpu", metric_name="cpu", condition=lambda v: v > 80, cooldown_seconds=0)
        manager = AlertManager()
        manager.add_rule(rule)
        for _ in range(5):
            manager.evaluate("cpu", 90.0)
        assert len(manager.get_history(limit=3)) == 3


class TestAlertRouter:
    def test_route_severity(self):
        received: list[str] = []

        def handler(alert):
            received.append(alert.severity)

        router = AlertRouter()
        router.add_route("critical", handler)
        alert = _alerts_mod.Alert(rule_name="r", message="m", severity="critical")
        router.route(alert)
        assert received == ["critical"]

    def test_route_many(self):
        received: list[str] = []

        def handler(alert):
            received.append(alert.severity)

        router = AlertRouter()
        router.add_route("warning", handler)
        alerts = [
            _alerts_mod.Alert(rule_name="r1", message="m1", severity="warning"),
            _alerts_mod.Alert(rule_name="r2", message="m2", severity="warning"),
        ]
        router.route_many(alerts)
        assert received == ["warning", "warning"]


class TestEscalationPolicy:
    def test_escalate(self):
        attempts: list[int] = []

        def handler(alert):
            attempts.append(alert.rule_name)

        policy = EscalationPolicy(escalation_chain=[{"handler": handler}], max_attempts=2)
        alert = _alerts_mod.Alert(rule_name="r", message="m", severity="critical")
        policy.escalate(alert, AlertRouter())
        policy.escalate(alert, AlertRouter())
        assert len(attempts) == 2
        policy.escalate(alert, AlertRouter())
        assert len(attempts) == 2


class TestDashboardEndpoints:
    def test_health(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.get("/observability/health")
        assert r.status_code == 200

    def test_dashboard_summary(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.get("/observability/dashboard")
        assert r.status_code == 200
        assert "gpu_utilization" in r.json()

    def test_record_gpu(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/gpu", json={"utilization": 55.0, "temperature": 60.0, "memory_used_mb": 1024.0})
        assert r.status_code == 200

    def test_record_tensor(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/tensor", json={"norm": 1.2, "layer": 0})
        assert r.status_code == 200

    def test_record_tokens(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/tokens", json={"tokens_per_second": 120.0, "prompt_tokens": 10, "completion_tokens": 20})
        assert r.status_code == 200

    def test_record_api_request(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/api", json={"latency_ms": 45.0, "status_code": 200, "endpoint": "/chat"})
        assert r.status_code == 200

    def test_record_benchmark(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/benchmark", json={"score": 0.92, "benchmark_name": "mmlu"})
        assert r.status_code == 200

    def test_record_dataset(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/dataset", json={"size": 5000, "domain": "docs"})
        assert r.status_code == 200

    def test_record_experiment(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.post("/observability/metrics/experiment", json={"count": 1})
        assert r.status_code == 200

    def test_list_alerts(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.get("/observability/alerts")
        assert r.status_code == 200
        assert "active" in r.json()

    def test_acknowledge_and_resolve(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        rule = AlertRule(name="test_rule", metric_name="cpu", condition=lambda v: v > 100)
        _dashboard_mod._alerts.add_rule(rule)
        _dashboard_mod._alerts.evaluate("cpu", 200.0)
        r = client.post("/observability/alerts/test_rule/acknowledge")
        assert r.status_code == 200
        r = client.post("/observability/alerts/test_rule/resolve")
        assert r.status_code == 200

    def test_metric_query(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        client.post("/observability/metrics/gpu", json={"utilization": 50.0})
        r = client.get("/observability/metrics/gpu")
        assert r.status_code == 200
        body = r.json()
        assert len(body["points"]) == 1

    def test_liveness_and_readiness(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(_dashboard_mod.router)
        client = TestClient(app)
        r = client.get("/observability/live")
        assert r.status_code == 200
        r = client.get("/observability/ready")
        assert r.status_code == 200
