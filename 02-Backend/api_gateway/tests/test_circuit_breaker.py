import time
import threading
import pytest
from api_gateway.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerProxy,
)


class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold == 5
        assert cfg.recovery_timeout == 30.0

    def test_custom_values(self):
        cfg = CircuitBreakerConfig(failure_threshold=10, recovery_timeout=60.0)
        assert cfg.failure_threshold == 10
        assert cfg.recovery_timeout == 60.0


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(name="test")
        s = cb.get_state("k1")
        assert s["state"] == "closed"

    def test_closed_allows_requests(self):
        cb = CircuitBreaker(name="test")
        assert cb.allow_request("k1") is True

    def test_record_failure_opens(self):
        cfg = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config=cfg, name="test")
        for _ in range(3):
            cb.allow_request("k1")
            cb.record_failure("k1")
        assert cb.get_state("k1")["state"] == "open"

    def test_open_denies_requests(self):
        cfg = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config=cfg, name="test")
        for _ in range(2):
            cb.allow_request("k1")
            cb.record_failure("k1")
        assert cb.allow_request("k1") is False

    def test_record_success_resets_failures(self):
        cb = CircuitBreaker(name="test")
        cb.allow_request("k1")
        cb.record_failure("k1")
        cb.record_success("k1")
        s = cb.get_state("k1")
        assert s["failure_count"] == 0

    def test_independent_keys(self):
        cb = CircuitBreaker(name="test")
        cfg = CircuitBreakerConfig(failure_threshold=2)
        cb._config = cfg
        for _ in range(2):
            cb.allow_request("a")
            cb.record_failure("a")
        assert cb.get_state("a")["state"] == "open"
        assert cb.get_state("b")["state"] == "closed"

    def test_reset_clears_state(self):
        cfg = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config=cfg, name="test")
        for _ in range(2):
            cb.allow_request("k1")
            cb.record_failure("k1")
        cb.reset("k1")
        assert cb.get_state("k1")["state"] == "closed"

    def test_name_property(self):
        cb = CircuitBreaker(name="my-circ")
        assert cb.name == "my-circ"

    def test_all_states(self):
        cb = CircuitBreaker(name="test")
        cb.allow_request("k1")
        assert "k1" in cb.all_states

    def test_disabled_circuit_open_after_threshold(self):
        cfg = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config=cfg, name="test")
        cb.allow_request("k1")
        cb.record_failure("k1")
        assert cb.get_state("k1")["state"] == "open"

    def test_half_open_after_recovery_timeout(self):
        cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker(config=cfg, name="test")
        cb.allow_request("k1")
        cb.record_failure("k1")
        assert cb.get_state("k1")["state"] == "open"
        time.sleep(0.2)
        assert cb.allow_request("k1") is True

    def test_success_count_resets_in_half_open(self):
        cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, success_threshold=2)
        cb = CircuitBreaker(config=cfg, name="test")
        cb.allow_request("k1")
        cb.record_failure("k1")
        time.sleep(0.2)
        assert cb.allow_request("k1") is True
        cb.record_success("k1")
        assert cb.get_state("k1")["state"] == "half_open"
        cb.record_success("k1")
        assert cb.get_state("k1")["state"] == "closed"

    def test_thread_safety(self):
        cb = CircuitBreaker(name="test")
        errors = []

        def worker():
            try:
                for _ in range(20):
                    if cb.allow_request("k1"):
                        cb.record_success("k1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_get_state_contains_failure_threshold(self):
        cb = CircuitBreaker(name="test")
        s = cb.get_state("k1")
        assert "failure_threshold" in s


class TestCircuitBreakerOpen:
    def test_raise_with_circuit_info(self):
        cb = CircuitBreaker(name="my-c")
        cb.allow_request("k1")
        cb.record_failure("k1")
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            raise CircuitBreakerOpen(cb.name, cb.get_state("k1")["opened_at"])
        assert "my-c" in str(exc_info.value)


class TestCircuitBreakerProxy:
    def test_call_succeeds(self):
        cb = CircuitBreaker(name="p")
        proxy = CircuitBreakerProxy(cb)
        result = proxy.call("k1", lambda: "ok")
        assert result == "ok"

    def test_call_raises_when_open(self):
        cfg = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config=cfg, name="p")
        proxy = CircuitBreakerProxy(cb)
        cb.allow_request("k1")
        cb.record_failure("k1")
        with pytest.raises(CircuitBreakerOpen):
            proxy.call("k1", lambda: "ok")

    def test_fallback_when_open(self):
        cb = CircuitBreaker(name="p")
        proxy = CircuitBreakerProxy(cb, fallback_func=lambda k: "fallback")
        cb.allow_request("k1")
        cb.record_failure("k1")
        result = proxy.call("k1", lambda: "ok")
        assert result == "fallback"

    def test_propagates_exception(self):
        cb = CircuitBreaker(name="p")
        proxy = CircuitBreakerProxy(cb)
        with pytest.raises(ValueError):
            proxy.call("k1", lambda: (_ for _ in ()).throw(ValueError("boom")))

    def test_records_success(self):
        cb = CircuitBreaker(name="p")
        proxy = CircuitBreakerProxy(cb)
        proxy.call("k1", lambda: "ok")
        assert cb.get_state("k1")["failure_count"] == 0

    def test_records_failure(self):
        cb = CircuitBreaker(name="p")
        proxy = CircuitBreakerProxy(cb)
        with pytest.raises(ValueError):
            proxy.call("k1", lambda: (_ for _ in ()).throw(ValueError("err")))
        assert cb.get_state("k1"]["failure_count"] == 1
