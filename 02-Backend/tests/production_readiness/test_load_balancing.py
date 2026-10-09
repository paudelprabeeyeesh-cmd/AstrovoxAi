from production_readiness.load_balancing import (
    LoadBalancer,
    LoadBalancingStrategy,
    BackendNode,
)


def _make_node(identifier):
    return BackendNode(id=str(identifier), host="127.0.0.1", port=8000 + identifier, weight=1, healthy=True)


def test_load_balancer_select_round_robin():
    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb.register(_make_node(1))
    lb.register(_make_node(2))
    first = lb.select()
    second = lb.select()
    assert first.id != second.id
    third = lb.select()
    assert third.id == first.id


def test_load_balancer_select_least_connections():
    lb = LoadBalancer(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
    lb.register(_make_node(1))
    lb.register(_make_node(2))
    first = lb.select()
    second = lb.select()
    assert first.id != second.id
    lb.release(second.id)
    third = lb.select()
    assert third.id == second.id


def test_load_balancer_health_check():
    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb.register(_make_node(1))
    lb.health_check("1", False)
    assert lb.nodes()[0].healthy is False


def test_load_balancer_status():
    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb.register(_make_node(1))
    status = lb.status()
    assert status["total"] == 1


def test_load_balancer_run_health_checks():
    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb.register(_make_node(1))
    results = lb.run_health_checks(lambda node: True)
    assert results["1"] is True
