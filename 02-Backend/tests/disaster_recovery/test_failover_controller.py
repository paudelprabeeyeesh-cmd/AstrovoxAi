from disaster_recovery.failover_controller import FailoverController, NodeState


def test_register_and_active_node():
    ctrl = FailoverController(active_node_id="node-a")
    ctrl.register_node("node-a", "a.example.com")
    ctrl.register_node("node-b", "b.example.com")
    assert ctrl.get_active_node() == "node-a"


def test_trigger_failover():
    ctrl = FailoverController(active_node_id="node-a")
    ctrl.register_node("node-a", "a.example.com")
    ctrl.register_node("node-b", "b.example.com")
    result = ctrl.trigger_failover("node-b")
    assert result["new_active"] == "node-b"
    assert ctrl.get_active_node() == "node-b"


def test_trigger_failover_unknown_node():
    ctrl = FailoverController(active_node_id="node-a")
    ctrl.register_node("node-a", "a.example.com")
    try:
        ctrl.trigger_failover("node-z")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_rollback():
    ctrl = FailoverController(active_node_id="node-a")
    ctrl.register_node("node-a", "a.example.com")
    ctrl.register_node("node-b", "b.example.com")
    ctrl.trigger_failover("node-b")
    result = ctrl.rollback()
    assert result is not None
    assert result["new_active"] == "node-a"
    assert ctrl.get_active_node() == "node-a"


def test_health_check():
    ctrl = FailoverController(active_node_id="node-a")
    ctrl.register_node("node-a", "a.example.com")
    assert ctrl.health_check("node-a") is True
    ctrl.mark_failed("node-a")
    assert ctrl.health_check("node-a") is False


def test_mark_failed_blocks_failover():
    ctrl = FailoverController(active_node_id="node-a")
    ctrl.register_node("node-a", "a.example.com")
    ctrl.register_node("node-b", "b.example.com")
    ctrl.mark_failed("node-b")
    try:
        ctrl.trigger_failover("node-b")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")
