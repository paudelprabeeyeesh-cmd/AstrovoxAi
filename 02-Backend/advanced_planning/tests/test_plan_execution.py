
from advanced_planning.plan_execution import ExecutionMonitor, ContingencyHandler


def _apply_fn(state, action):
    if action == "fail":
        raise RuntimeError("boom")
    new = dict(state)
    new["step"] = new.get("step", 0) + 1
    return new


def _goal_fn(state):
    return state.get("step", 0) >= 3


def test_execution_monitor_success():
    monitor = ExecutionMonitor(["go", "go", "go"], _apply_fn, _goal_fn)
    result = monitor.execute({"step": 0})
    assert result["goal_reached"] is True
    assert monitor.current_index == 3
    assert not monitor.has_contingency()


def test_execution_monitor_progress():
    monitor = ExecutionMonitor(["go", "go", "go"], _apply_fn, _goal_fn)
    monitor.execute({"step": 0})
    assert monitor.get_progress() == 1.0


def test_execution_monitor_contingency():
    monitor = ExecutionMonitor(["fail", "go"], _apply_fn, _goal_fn)
    monitor.execute({"step": 0})
    assert monitor.has_contingency()
    assert len(monitor.contingencies_triggered) == 1
    assert monitor.current_index == 0


def test_execution_monitor_execution_log():
    monitor = ExecutionMonitor(["go"], _apply_fn, _goal_fn)
    monitor.execute({"step": 0})
    assert len(monitor.execution_log) == 2
    assert monitor.execution_log[0]["status"] == "start"
    assert monitor.execution_log[1]["status"] == "success"


def test_contingency_handler_recovery():
    handler = ContingencyHandler({"timeout": ["restart", "retry"]})
    recovery = handler.handle_error("timeout", {})
    assert recovery == ["restart", "retry"]


def test_contingency_handler_unknown_error():
    handler = ContingencyHandler({})
    recovery = handler.handle_error("unknown", {})
    assert recovery is None


def test_contingency_execute_recovery():
    def safe_apply(state, action):
        return {"step": state.get("step", 0) + 1}

    handler = ContingencyHandler({})
    result = handler.execute_recovery(["retry", "retry"], safe_apply, {"step": 0})
    assert result["success"] is True
    assert result["state"]["step"] == 2


def test_contingency_execute_recovery_with_error():
    def fail_apply(state, action):
        raise RuntimeError()

    handler = ContingencyHandler({})
    result = handler.execute_recovery(["fail"], fail_apply, {"step": 0})
    assert result["success"] is False
