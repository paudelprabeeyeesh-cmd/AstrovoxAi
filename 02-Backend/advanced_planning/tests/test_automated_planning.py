
from advanced_planning.automated_planning import Predicate, Action, PlanningProblem, GraphPlan, HeuristicPlanner


def test_predicate_repr():
    p = Predicate("at", ("robot", "room_a"))
    assert "at" in repr(p)


def test_predicate_equality():
    p1 = Predicate("at", ("r", "a"))
    p2 = Predicate("at", ("r", "a"))
    p3 = Predicate("at", ("r", "b"))
    assert p1 == p2
    assert p1 != p3


def test_predicate_hash():
    p1 = Predicate("on", ("a", "b"))
    p2 = Predicate("on", ("a", "b"))
    assert hash(p1) == hash(p2)
    s = {p1, p2}
    assert len(s) == 1


def test_action_grounding():
    pre = {Predicate("At", ("?r", "?x"))}
    add = {Predicate("At", ("?r", "?y"))}
    action = Action("Move", ("?r", "?x", "?y"), pre, add, set())
    grounded = action.ground({"?r": "robot1", "?x": "A", "?y": "B"})
    assert grounded.name == "Move"
    assert Predicate("At", ("robot1", "B")) in grounded.add_effects


def test_planning_problem_is_goal():
    initial = {Predicate("At", ("r", "A"))}
    goal = {Predicate("At", ("r", "B"))}
    actions = []
    prob = PlanningProblem(initial, goal, actions, {})
    assert not prob.is_goal(initial)
    new_state = {Predicate("At", ("r", "B"))}
    assert prob.is_goal(new_state)


def test_graph_plan_finds_plan():
    at_r_A = Predicate("At", ("r", "A"))
    at_r_B = Predicate("At", ("r", "B"))
    initial = {at_r_A}
    goal = {at_r_B}
    move = Action("Move", ("r", "A", "B"),
                  preconditions={Predicate("At", ("r", "A"))},
                  add_effects={Predicate("At", ("r", "B"))},
                  del_effects={Predicate("At", ("r", "A"))},
                  cost=1.0)
    prob = PlanningProblem(initial, goal, [move], {"r": ["r"], "loc": ["A", "B"]})
    gp = GraphPlan(prob)
    found = gp.build(max_levels=10)
    assert found
    plan = gp.extract_plan()
    assert plan is not None
    assert len(plan) >= 1


def test_graph_plan_no_solution():
    at_r_A = Predicate("At", ("r", "A"))
    at_r_C = Predicate("At", ("r", "C"))
    initial = {at_r_A}
    goal = {at_r_C}
    move_a2b = Action("MoveAB", ("r",),
                      preconditions={Predicate("At", ("r", "A"))},
                      add_effects={Predicate("At", ("r", "B"))},
                      del_effects={Predicate("At", ("r", "A"))})
    move_b2a = Action("MoveBA", ("r",),
                      preconditions={Predicate("At", ("r", "B"))},
                      add_effects={Predicate("At", ("r", "A"))},
                      del_effects={Predicate("At", ("r", "B"))})
    prob = PlanningProblem(initial, goal, [move_a2b, move_b2a], {"r": ["r"], "loc": ["A", "B", "C"]})
    gp = GraphPlan(prob)
    found = gp.build(max_levels=5)
    assert not found


def test_heuristic_planner_reaches_goal():
    at_r_A = Predicate("At", ("r", "A"))
    at_r_B = Predicate("At", ("r", "B"))
    initial = {at_r_A}
    goal = {at_r_B}
    move = Action("Move", ("r", "A", "B"),
                  preconditions={Predicate("At", ("r", "A"))},
                  add_effects={Predicate("At", ("r", "B"))},
                  del_effects={Predicate("At", ("r", "A"))})
    prob = PlanningProblem(initial, goal, [move], {"r": ["r"], "loc": ["A", "B"]})
    planner = HeuristicPlanner(prob)
    plan = planner.plan(max_steps=10)
    assert plan is not None
    assert len(plan) >= 1


def test_heuristic_planner_no_action_returns_none():
    initial = {Predicate("At", ("r", "A"))}
    goal = {Predicate("At", ("r", "B"))}
    prob = PlanningProblem(initial, goal, [], {"r": ["r"], "loc": ["A", "B"]})
    planner = HeuristicPlanner(prob)
    plan = planner.plan(max_steps=5)
    assert plan is None


def test_apply_action_changes_state():
    at_r_A = Predicate("At", ("r", "A"))
    at_r_y = Predicate("At", ("r", "y"))
    state = {at_r_A}
    move = Action("Move", ("r", "A", "y"),
                  preconditions={Predicate("At", ("r", "A"))},
                  add_effects={at_r_y},
                  del_effects={at_r_A})
    planner = HeuristicPlanner(None)
    new_state = planner._apply_action(state, move)
    assert at_r_A not in new_state
    assert at_r_y in new_state
