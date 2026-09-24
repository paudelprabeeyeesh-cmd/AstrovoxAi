import threading

from scalability_patterns.load_balancer import RoundRobinLoadBalancer, WeightedLoadBalancer


def test_round_robin_select():
    rb = RoundRobinLoadBalancer(nodes=["a", "b", "c"])
    selected = [rb.select() for _ in range(6)]
    assert selected == ["a", "b", "c", "a", "b", "c"]


def test_round_robin_add_remove():
    rb = RoundRobinLoadBalancer()
    rb.add_node("x")
    assert rb.select() == "x"
    rb.remove_node("x")
    assert rb.select() is None


def test_weighted_select_distribution():
    wb = WeightedLoadBalancer(weights={"a": 3, "b": 1})
    selected = [wb.select() for _ in range(4)]
    assert selected.count("a") == 3
    assert selected.count("b") == 1


def test_weighted_remove():
    wb = WeightedLoadBalancer(weights={"a": 1})
    wb.remove_node("a")
    assert wb.select() is None


def test_round_robin_thread_safety():
    rb = RoundRobinLoadBalancer(nodes=["a", "b"])
    results = []

    def select_many():
        for _ in range(100):
            results.append(rb.select())

    threads = [threading.Thread(target=select_many) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2)
    assert len(results) == 400
    assert all(v in ("a", "b") for v in results)
