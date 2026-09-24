import threading
import time
import pytest
from api_gateway.load_balancer import (
    LoadBalancer,
    Strategy,
    BackendNode,
    RoutingDecision,
)


class TestLoadBalancer:
    def test_add_node(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        assert lb.node_count == 1
        assert lb.healthy_count == 1

    def test_add_multiple_nodes(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        assert lb.node_count == 2
        assert lb.healthy_count == 2

    def test_remove_node(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.remove_node("n1")
        assert lb.node_count == 0
        assert lb.healthy_count == 0

    def test_route_round_robin(self):
        lb = LoadBalancer(Strategy.ROUND_ROBIN)
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        first = lb.route()
        lb.release(first.node_id)
        second = lb.route()
        assert first.node_id != second.node_id

    def test_route_no_nodes_raises(self):
        lb = LoadBalancer()
        with pytest.raises(ValueError):
            lb.route()

    def test_route_skips_unhealthy(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        lb.mark_unhealthy("n1")
        decision = lb.route()
        assert decision.node_id == "n2"

    def test_round_robin_respects_order(self):
        lb = LoadBalancer(Strategy.ROUND_ROBIN)
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        lb.add_node("n3", "10.0.0.3", 8080)
        decisions = []
        for _ in range(3):
            d = lb.route()
            decisions.append(d.node_id)
            lb.release(d.node_id)
        assert len(set(decisions)) == 3

    def test_least_connections(self):
        lb = LoadBalancer(Strategy.LEAST_CONNECTIONS)
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        lb.route()
        lb.route()
        lb.route()
        decision = lb.route()
        assert decision.node_id == "n2"

    def test_weighted_round_robin(self):
        lb = LoadBalancer(Strategy.WEIGHTED_ROUND_ROBIN)
        lb.add_node("n1", "10.0.0.1", 8080, weight=3)
        lb.add_node("n2", "10.0.0.2", 8080, weight=1)
        decisions = []
        for _ in range(8):
            d = lb.route()
            decisions.append(d.node_id)
            lb.release(d.node_id)
        assert decisions.count("n1") > decisions.count("n2")

    def test_random(self):
        lb = LoadBalancer(Strategy.RANDOM)
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        lb.add_node("n3", "10.0.0.3", 8080)
        decisions = []
        for _ in range(30):
            decisions.append(lb.route().node_id)
        assert "n1" in decisions
        assert "n2" in decisions

    def test_ip_hash(self):
        lb = LoadBalancer(Strategy.IP_HASH)
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        d1 = lb.route(client_ip="1.2.3.4")
        d2 = lb.route(client_ip="1.2.3.4")
        assert d1.node_id == d2.node_id

    def test_ip_hash_consistent_across_nodes(self):
        lb = LoadBalancer(Strategy.IP_HASH)
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.add_node("n2", "10.0.0.2", 8080)
        lb.add_node("n3", "10.0.0.3", 8080)
        client_ip = "10.10.10.10"
        decisions = []
        for _ in range(20):
            decisions.append(lb.route(client_ip=client_ip).node_id)
        assert len(set(decisions)) == 1

    def test_mark_unhealthy(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.mark_unhealthy("n1")
        assert lb.healthy_count == 0

    def test_mark_healthy(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.mark_unhealthy("n1")
        lb.mark_healthy("n1")
        assert lb.healthy_count == 1

    def test_release_reduces_connections(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        d = lb.route()
        assert d.node_id == "n1"
        lb.release("n1")
        nodes = lb.all_nodes
        assert nodes["n1"]["active_connections"] == 0

    def test_record_response_time(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080)
        lb.record_response_time("n1", 150.0)
        assert lb.all_nodes["n1"]["response_time_ms"] == 150.0

    def test_strategy_property(self):
        lb = LoadBalancer(Strategy.LEAST_CONNECTIONS)
        assert lb.strategy == "least_connections"

    def test_all_nodes_dict(self):
        lb = LoadBalancer()
        lb.add_node("n1", "10.0.0.1", 8080, weight=5)
        nodes = lb.all_nodes
        assert nodes["n1"]["weight"] == 5
        assert nodes["n1"]["is_healthy"] is True

    def test_thread_safety_route(self):
        lb = LoadBalancer(Strategy.ROUND_ROBIN)
        for i in range(10):
            lb.add_node(f"n{i}", f"10.0.0.{i}", 8080)
        decisions = []
        errors = []

        def worker():
            try:
                for _ in range(50):
                    d = lb.route()
                    decisions.append(d.node_id)
                    lb.release(d.node_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(decisions) == 500

    def test_routing_decision_attributes(self):
        lb = LoadBalancer(Strategy.IP_HASH)
        lb.add_node("n1", "10.0.0.1", 8080)
        d = lb.route(client_ip="5.5.5.5")
        assert d.host == "10.0.0.1"
        assert d.port == 8080
        assert d.strategy == "ip_hash"
        assert d.ip_hash_used is True
