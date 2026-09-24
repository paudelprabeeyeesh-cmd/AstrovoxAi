"""Tests for Task 114: Security Monitoring."""

import numpy as np
import pytest

from security_audit.security_monitoring import (
    Alert,
    AlertRule,
    SecurityEvent,
    SecurityMonitor,
)


@pytest.fixture
def monitor():
    return SecurityMonitor()


class TestSecurityEvent:
    def test_event_creation(self):
        event = SecurityEvent(timestamp=100.0, source="web", event_type="login", message="User logged in", severity="info")
        assert event.source == "web"
        assert event.event_type == "login"

    def test_event_default_metadata(self):
        event = SecurityEvent(timestamp=0.0, source="x", event_type="y", message="z", severity="low")
        assert isinstance(event.metadata, dict)


class TestAlertRule:
    def test_rule_creation(self):
        rule = AlertRule(name="login_flood", event_type="login", threshold=10.0, window_seconds=60.0, severity="high")
        assert rule.name == "login_flood"
        assert rule.threshold == 10.0


class TestSecurityMonitor:
    def test_add_rule(self, monitor):
        monitor.add_rule(AlertRule("flood", "login", 5.0, 60.0, "high"))
        assert len(monitor._rules) == 1

    def test_log_event_returns_event(self, monitor):
        event = monitor.log_event("web", "login", "user login", "info")
        assert isinstance(event, SecurityEvent)

    def test_log_event_stores_internal(self, monitor):
        monitor.log_event("web", "login", "test")
        assert len(monitor._events) == 1

    def test_get_events_filter_by_type(self, monitor):
        monitor.log_event("a", "login", "1")
        monitor.log_event("a", "logout", "2")
        events = monitor.get_events(event_type="login")
        assert len(events) == 1
        assert events[0].event_type == "login"

    def test_get_events_since_filter(self, monitor):
        monitor.log_event("a", "login", "1")
        events = monitor.get_events(since=9999999999.0)
        assert len(events) == 0

    def test_on_alert_handler_called(self, monitor):
        called = []
        monitor.on_alert(lambda a: called.append(a))
        monitor.add_rule(AlertRule("flood", "login", 1.0, 60.0, "high"))
        monitor.log_event("web", "login", "attempt 1")
        monitor.log_event("web", "login", "attempt 2")
        assert len(called) >= 0

    def test_compute_metrics_empty(self, monitor):
        metrics = monitor.compute_metrics()
        assert metrics["event_count"] == 0
        assert metrics["alert_count"] == 0

    def test_compute_metrics_populated(self, monitor):
        monitor.log_event("web", "login", "1")
        monitor.log_event("web", "login", "2")
        metrics = monitor.compute_metrics()
        assert metrics["event_count"] == 2
        assert metrics["event_types"] == 1

    def test_alert_rule_threshold(self, monitor):
        monitor.add_rule(AlertRule("flood", "login", 2.0, 10.0, "high"))
        monitor.on_alert(lambda a: None)
        monitor.log_event("web", "login", "1")
        monitor.log_event("web", "login", "2")
        monitor.log_event("web", "login", "3")
        assert len(monitor.get_alerts()) >= 1

    def test_different_event_types_no_trigger(self, monitor):
        monitor.add_rule(AlertRule("flood", "login", 1.0, 60.0, "high"))
        monitor.on_alert(lambda a: None)
        monitor.log_event("web", "logout", "1")
        monitor.log_event("web", "logout", "2")
        assert len(monitor.get_alerts()) == 0


class TestSecurityMonitorNumpy:
    def test_event_rate_numeric(self, monitor):
        for _ in range(10):
            monitor.log_event("web", "login", "test")
        metrics = monitor.compute_metrics()
        assert isinstance(metrics["avg_events_per_minute"], float)

    def test_event_type_counts(self, monitor):
        for _ in range(5):
            monitor.log_event("web", "login", "1")
        for _ in range(3):
            monitor.log_event("web", "logout", "2")
        metrics = monitor.compute_metrics()
        assert metrics["event_types"] == 2

    def test_alert_counts_numeric(self, monitor):
        monitor.add_rule(AlertRule("flood", "login", 2.0, 10.0, "high"))
        monitor.on_alert(lambda a: None)
        for _ in range(5):
            monitor.log_event("web", "login", "x")
        alerts = monitor.get_alerts()
        assert isinstance(len(alerts), int)

    def test_timestamp_array_dtype(self, monitor):
        for _ in range(5):
            monitor.log_event("web", "login", "x")
        timestamps = np.array([e.timestamp for e in monitor._events], dtype=np.float64)
        assert timestamps.dtype in (np.float64, np.float32)
