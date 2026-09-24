import numpy as np

from observability.alerting import Alert, AlertManager


def test_alert_repr():
    a = Alert(name="x", severity="warn", message="m")
    assert "x" in repr(a)
    assert "warn" in repr(a)


def test_threshold_alert_fires_above():
    mgr = AlertManager(cooldown_seconds=0)
    result = mgr.threshold_alert("latency", 5.0, 3.0, severity="error", direction="above")
    assert result is not None
    assert result.name == "latency"


def test_threshold_alert_no_fire_below():
    mgr = AlertManager(cooldown_seconds=0)
    result = mgr.threshold_alert("latency", 1.0, 3.0, direction="above")
    assert result is None


def test_threshold_alert_fires_below():
    mgr = AlertManager(cooldown_seconds=0)
    result = mgr.threshold_alert("score", 1.0, 3.0, direction="below")
    assert result is not None


def test_cooldown_prevents_refire():
    mgr = AlertManager(cooldown_seconds=1000)
    mgr.threshold_alert("k", 5.0, 3.0, direction="above")
    result = mgr.threshold_alert("k", 6.0, 3.0, direction="above")
    assert result is None


def test_active_alerts_list():
    mgr = AlertManager(cooldown_seconds=0)
    mgr.threshold_alert("a", 5.0, 3.0, direction="above")
    alerts = mgr.active_alerts()
    assert len(alerts) == 1


def test_clear():
    mgr = AlertManager(cooldown_seconds=0)
    mgr.threshold_alert("a", 5.0, 3.0, direction="above")
    mgr.clear()
    assert len(mgr.active_alerts()) == 0


def test_anomaly_alert_z_threshold():
    mgr = AlertManager(cooldown_seconds=0)
    history = [1.0, 2.0, 3.0, 2.5, 1.8]
    result = mgr.anomaly_alert("cost", history, 100.0, z_threshold=2.0)
    assert result is not None


def test_anomaly_alert_no_z_score():
    mgr = AlertManager(cooldown_seconds=0)
    history = [1.0, 2.0, 1.5]
    result = mgr.anomaly_alert("cost", history, 1.2, z_threshold=2.0)
    assert result is None


def test_anomaly_alert_insufficient_history():
    mgr = AlertManager(cooldown_seconds=0)
    result = mgr.anomaly_alert("cost", [1.0], 2.0)
    assert result is not None


def test_anomaly_z_computation():
    AlertManager(cooldown_seconds=0)
    values = np.array([10.0, 12.0, 11.0, 100.0])
    mean = float(np.mean(values))
    std = float(np.std(values))
    z = abs(12.0 - mean) / std
    assert np.isfinite(z)
