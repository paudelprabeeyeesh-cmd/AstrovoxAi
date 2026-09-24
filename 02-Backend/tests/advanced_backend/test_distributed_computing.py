import time
import pytest
from advanced_backend.distributed_computing import DistributedExecutor, LoadBalancer


def test_load_balancer_round_robin():
    lb = LoadBalancer(strategy="round_robin")
    lb.register_node("a")
    lb.register_node("b")
    lb.register_node("c")
    seq = [lb.select_node() for _ in range(6)]
    assert seq == ["a", "b", "c", "a", "b", "c"]


def test_load_balancer_weighted():
    lb = LoadBalancer(strategy="weighted")
    lb.register_node("a", weight=0)
    lb.register_node("b", weight=10)
    choices = [lb.select_node() for _ in range(50)]
    assert all(c == "b" for c in choices)


def test_load_balancer_unregister():
    lb = LoadBalancer(strategy="round_robin")
    lb.register_node("a")
    lb.register_node("b")
    lb.unregister_node("a")
    choices = [lb.select_node() for _ in range(10)]
    assert all(c == "b" for c in choices)


def test_distributed_executor_submit_and_get():
    ex = DistributedExecutor(num_workers=2)
    ex.start()
    ready = threading.Event()
    def slow_double(x):
        ready.set()
        return x * 2
    tid = ex.submit(slow_double, 21)
    ready.wait(timeout=2)
    result = ex.get_result(tid, timeout=10.0)
    assert result == 42


def test_distributed_executor_metrics():
    ex = DistributedExecutor(num_workers=1)
    ex.start()
    ex.submit(lambda: 1)
    m = ex.metrics()
    assert "pending" in m and "processing" in m and "completed" in m
