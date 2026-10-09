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


def test_round_robin_nodes_method():
    rb = RoundRobinLoadBalancer(nodes=["a", "b"])
    assert rb.nodes() == ["a", "b"]


def test_weighted_nodes_method():
    wb = WeightedLoadBalancer(weights={"a": 2, "b": 1})
    assert wb.nodes() == ["a", "b"]


def test_weighted_add_node():
    wb = WeightedLoadBalancer()
    wb.add_node("x", weight=5)
    selected = [wb.select() for _ in range(5)]
    assert selected.count("x") == 5


def test_round_robin_empty_select():
    rb = RoundRobinLoadBalancer()
    assert rb.select() is None


def test_weighted_empty_select():
    wb = WeightedLoadBalancer()
    assert wb.select() is None


def test_weighted_equal_weights():
    wb = WeightedLoadBalancer(weights={"a": 1, "b": 1})
    selected = [wb.select() for _ in range(4)]
    assert selected.count("a") == 2
    assert selected.count("b") == 2


def test_round_robin_remove_missing():
    rb = RoundRobinLoadBalancer(nodes=["a"])
    rb.remove_node("missing")
    assert rb.select() == "a"


def test_weighted_remove_missing():
    wb = WeightedLoadBalancer(weights={"a": 1})
    wb.remove_node("missing")
    assert wb.select() == "a"


def test_weighted_thread_safety():
    wb = WeightedLoadBalancer(weights={"a": 1, "b": 1})
    results = []

    def select_many():
        for _ in range(100):
            results.append(wb.select())

    threads = [threading.Thread(target=select_many) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2)
    assert len(results) == 400
    assert all(v in ("a", "b") for v in results)
