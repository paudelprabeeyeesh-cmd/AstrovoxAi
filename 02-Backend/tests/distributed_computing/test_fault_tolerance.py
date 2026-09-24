import time
import threading

from distributed_computing.fault_tolerance import FailureDetector, HeartbeatMonitor, RetryPolicy


def boom():
    raise RuntimeError("fail")


def ok():
    return "ok"


def test_retry_success():
    policy = RetryPolicy(max_retries=3, backoff=0.01)
    result = policy.execute(ok)
    assert result == "ok"


def test_retry_exhausted():
    policy = RetryPolicy(max_retries=2, backoff=0.01)
    try:
        policy.execute(boom)
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass
    assert policy.attempts() == 2


def test_retry_reset():
    policy = RetryPolicy(max_retries=2, backoff=0.01)
    try:
        policy.execute(boom)
    except RuntimeError:
        pass
    policy.reset()
    assert policy.attempts() == 0


def test_heartbeat_check_alive():
    hb = HeartbeatMonitor(node_id="n1", timeout=1.0)
    hb.pulse()
    assert hb.check() is True


def test_heartbeat_check_dead():
    hb = HeartbeatMonitor(node_id="n1", timeout=0.05)
    time.sleep(0.1)
    assert hb.check() is False


def test_failure_detector():
    dead_nodes = []

    def on_dead(node_id):
        dead_nodes.append(node_id)

    fd = FailureDetector(timeout=0.1)
    fd.register("n1", on_dead)
    time.sleep(0.15)
    assert "n1" in fd.dead_nodes()
