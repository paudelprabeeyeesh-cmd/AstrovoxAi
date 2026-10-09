
from advanced_planning.plan_execution import ExecutionMonitor, ContingencyHandler


def test_execution_monitor_success():
    def apply_fn(state, action):
        state = dict(state)
        state["value"] = state.get("value", 0) + action
        return state

    def goal_fn(state):
        return state.get("value", 0) >= 5

    monitor = ExecutionMonitor([1, 2, 3], apply_fn, goal_fn)
    result = monitor.execute({"value": 0})
    assert result["goal_reached"] is True
    assert result["completed_steps"] == 3
    assert result["final_state"]["value"] == 6


def test_execution_monitor_goal_reached_early():
    def apply_fn(state, action):
        state = dict(state)
        state["x"] = state.get("x", 0) + action
        return state

    def goal_fn(state):
        return state.get("x", 0) >= 3

    monitor = ExecutionMonitor([1, 2, 100], apply_fn, goal_fn)
    result = monitor.execute({"x": 0})
    assert result["goal_reached"] is True
    assert result["completed_steps"] == 2


def test_execution_monitor_error_triggers_contingency():
    def apply_fn(state, action):
        if action == "fail":
            raise RuntimeError("boom")
        return dict(state)

    def goal_fn(state):
        return False

    monitor = ExecutionMonitor(["ok", "fail", "ok"], apply_fn, goal_fn)
    result = monitor.execute({})
    assert result["goal_reached"] is False
    assert monitor.has_contingency() is True
    assert len(monitor.contingencies_triggered) == 1
    assert monitor.contingencies_triggered[0]["error"] == "boom"
    assert result["completed_steps"] == 1


def test_execution_monitor_progress():
    monitor = ExecutionMonitor([1, 2, 3], lambda s, a: s, lambda s: False)
    assert monitor.get_progress() == 0.0
    monitor.execute({})
    assert monitor.get_progress() == 1.0


def test_execution_monitor_empty_plan():
    monitor = ExecutionMonitor([], lambda s, a: s, lambda s: True)
    result = monitor.execute({})
    assert result["goal_reached"] is True
    assert result["completed_steps"] == 0
    assert result["contingencies"] == []


def test_execution_monitor_logs_initial_and_final():

    def apply_fn(state, action):
        return {"step": state.get("step", 0) + 1}

    monitor = ExecutionMonitor([1], apply_fn, lambda s: s.get("step", 0) >= 1)
    monitor.execute({"step": 0})
    assert monitor.execution_log[0]["status"] == "start"
    assert any(entry["status"] == "goal_reached" for entry in monitor.execution_log)


def test_contingency_handler_known_error():
    handler = ContingencyHandler({"timeout": ["retry", "abort"]})
    plan = handler.handle_error("timeout", {})
    assert plan == ["retry", "abort"]
    assert len(handler.executed_recoveries) == 1
    assert handler.executed_recoveries[0]["error_type"] == "timeout"


def test_contingency_handler_unknown_error():
    handler = ContingencyHandler({"timeout": ["retry"]})
    plan = handler.handle_error("unknown", {})
    assert plan is None
    assert len(handler.executed_recoveries) == 0


def test_contingency_handler_execute_recovery_all_success():
    def apply_fn(state, action):
        return dict(state)

    handler = ContingencyHandler()
    result = handler.execute_recovery(["a", "b"], apply_fn, {})
    assert result["success"] is True
    assert len(result["log"]) == 2


def test_contingency_handler_execute_recovery_partial_failure():
    call_count = [0]

    def apply_fn(state, action):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("fail")
        return dict(state)

    handler = ContingencyHandler()
    result = handler.execute_recovery(["a", "b", "c"], apply_fn, {})
    assert result["success"] is False
    assert result["log"][1]["status"] == "error"


def test_contingency_handler_empty_recovery_plan():
    handler = ContingencyHandler()
    result = handler.execute_recovery([], lambda s, a: s, {})
    assert result["success"] is True
    assert result["log"] == []
