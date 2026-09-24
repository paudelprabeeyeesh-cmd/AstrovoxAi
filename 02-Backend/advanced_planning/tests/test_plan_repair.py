
from advanced_planning.plan_repair import Plan, PlanRepairEngine, Replanner


def _is_valid_fn(plan: Plan) -> bool:
    return all(a != "bad" for a in plan.actions)


def _apply_fn(state, action):
    if action == "bad":
        raise ValueError("bad action")
    return state + [action]


def _get_actions_fn(state):
    return ["go", "wait"]


def _is_goal(state):
    return len(state) >= 3


def _heuristic(state):
    return max(0, 3 - len(state))


def test_plan_initialization():
    plan = Plan(["a", "b", "c"])
    assert len(plan) == 3
    assert plan.valid is True


def test_plan_repair_engine_no_failure():
    engine = PlanRepairEngine(_is_valid_fn, _apply_fn, _get_actions_fn)
    plan = Plan(["go", "go"])
    repaired = engine.repair_remove(plan, [])
    assert len(repaired) == 2


def test_plan_repair_engine_failure_diagnosis():
    engine = PlanRepairEngine(_is_valid_fn, _apply_fn, _get_actions_fn)
    plan = Plan(["go", "bad"])
    idx = engine.diagnose(plan, [])
    assert idx == 1


def test_plan_repair_engine_remove():
    engine = PlanRepairEngine(_is_valid_fn, _apply_fn, _get_actions_fn)
    plan = Plan(["go", "bad"])
    repaired = engine.repair_remove(plan, [])
    assert repaired.valid
    assert len(repaired) == 1


def test_replanner_finds_plan():
    replanner = Replanner(_is_goal, _get_actions_fn, _apply_fn, _heuristic)
    plan = replanner.replan([], Plan([]), max_actions=5)
    assert plan is not None
    assert plan.valid is True
    assert len(plan.actions) >= 3


def test_replanner_count():
    replanner = Replanner(_is_goal, _get_actions_fn, _apply_fn, _heuristic)
    replanner.replan([], Plan([]), max_actions=5)
    assert replanner.replan_count == 1


def test_plan_repair_history():
    engine = PlanRepairEngine(_is_valid_fn, _apply_fn, _get_actions_fn)
    plan = Plan(["go", "bad", "go"])
    engine.repair_remove(plan, [])
    assert len(engine.repair_history) == 1
    assert engine.repair_history[0]["type"] == "remove"
