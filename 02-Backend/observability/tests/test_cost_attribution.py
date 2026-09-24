import numpy as np
import pytest

from observability.cost_attribution import CostAttribution


def test_record_and_total_cost():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u1", "chat", "gpt-4", 0.03, 50)
    assert ca.total_cost() == pytest.approx(0.08)


def test_cost_by_user():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u2", "chat", "gpt-4", 0.07, 200)
    result = ca.cost_by_user()
    assert result["u1"] == pytest.approx(0.05)
    assert result["u2"] == pytest.approx(0.07)


def test_cost_by_feature():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u1", "code", "gpt-4", 0.03, 50)
    result = ca.cost_by_feature()
    assert result["chat"] == pytest.approx(0.05)
    assert result["code"] == pytest.approx(0.03)


def test_cost_by_model():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u1", "chat", "gpt-3.5", 0.01, 200)
    result = ca.cost_by_model()
    assert result["gpt-4"] == pytest.approx(0.05)
    assert result["gpt-3.5"] == pytest.approx(0.01)


def test_cost_by_user_feature():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u1", "code", "gpt-4", 0.03, 50)
    result = ca.cost_by_user_feature()
    assert result["u1"]["chat"] == pytest.approx(0.05)
    assert result["u1"]["code"] == pytest.approx(0.03)


def test_cost_by_feature_model():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u2", "chat", "gpt-3.5", 0.02, 200)
    result = ca.cost_by_feature_model()
    assert result["chat"]["gpt-4"] == pytest.approx(0.05)
    assert result["chat"]["gpt-3.5"] == pytest.approx(0.02)


def test_cost_by_user_model():
    ca = CostAttribution()
    ca.record("u1", "chat", "gpt-4", 0.05, 100)
    ca.record("u1", "chat", "gpt-3.5", 0.02, 200)
    result = ca.cost_by_user_model()
    assert result["u1"]["gpt-4"] == pytest.approx(0.05)
    assert result["u1"]["gpt-3.5"] == pytest.approx(0.02)


def test_empty_total_cost():
    ca = CostAttribution()
    assert ca.total_cost() == pytest.approx(0.0)


def test_thread_safety():
    ca = CostAttribution()
    import threading

    def worker():
        for _ in range(100):
            ca.record("u1", "chat", "gpt-4", 0.01, 10)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert ca.total_cost() == pytest.approx(4 * 100 * 0.01)
