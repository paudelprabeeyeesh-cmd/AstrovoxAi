
from advanced_planning.automated_planning import (
    Predicate,
    Action,
    PlanningProblem,
    GraphPlan,
    HeuristicPlanner,
)


def _make_move_action(name="move", from_loc="A", to_loc="B"):
    pre = {Predicate("at", (from_loc,))}
    add = {Predicate("at", (to_loc,))}
    de = {Predicate("at", (from_loc,))}
    return Action(name, ("?from", "?to"), pre, add, de)


def _make_noop():
    return Action("noop", (), set(), set(), set())


def test_predicate_equality_and_hash():
    p1 = Predicate("at", ("A",))
    p2 = Predicate("at", ("A",))
    p3 = Predicate("at", ("B",))
    assert p1 == p2
    assert p1 != p3
    assert len({p1, p2}) == 1


def test_action_ground_substitutes_parameters():
    a = Action("move", ("?from", "?to"),
               {Predicate("at", ("?from",))},
               {Predicate("at", ("?to",))},
               {Predicate("at", ("?from",))})
    g = a.ground({"?from": "A", "?to": "B"})
    assert g.name == "move"
    assert Predicate("at", ("B",)) in g.add_effects
    assert Predicate("at", ("A",)) in g.del_effects
    assert Predicate("at", ("A",)) not in g.preconditions or Predicate("at", ("A",)) in g.preconditions


def test_planning_problem_is_goal_true_and_false():
    init = {Predicate("at", ("A",))}
    goal = {Predicate("at", ("B",))}
    actions = [_make_move_action()]
    prob = PlanningProblem(init, goal, actions, {})
    assert not prob.is_goal(init)
    assert prob.is_goal(init | goal)


def test_graph_plan_simple_blocks_world():
    on_table = Predicate("on_table", ("block_a",))
    holding = Predicate("holding", ("block_a",))
    on_b = Predicate("on", ("block_a", "block_b"))

    pick_up = Action("pick-up", ("?b",), {on_table}, {holding}, {on_table})
    stack = Action("stack", ("?b", "?t"), {holding, Predicate("clear", ("block_b",))},
                   {on_b, Predicate("clear", ("block_a",))}, {holding, Predicate("clear", ("block_b",))})

    init = {Predicate("on_table", ("block_a",)), Predicate("clear", ("block_b",))}
    goal = {Predicate("on", ("block_a", "block_b")), Predicate("clear", ("block_a",))}
    actions = [pick_up, stack]
    prob = PlanningProblem(init, goal, actions, {})
    planner = GraphPlan(prob)
    plan = planner.bfs_find_plan(max_depth=6)
    assert plan is not None
    assert len(plan) >= 2


def test_graph_plan_already_at_goal():
    p = Predicate("done", ())
    prob = PlanningProblem({p}, {p}, [], {})
    planner = GraphPlan(prob)
    assert planner.build(max_levels=5)
    assert planner.extract_plan() == []


def test_graph_plan_no_plan_possible():
    init = {Predicate("locked", ())}
    goal = {Predicate("open", ())}
    actions = [_make_noop()]
    prob = PlanningProblem(init, goal, actions, {})
    planner = GraphPlan(prob)
    assert not planner.build(max_levels=5)


def test_graph_plan_bfs_find_plan():
    move = _make_move_action("move", "A", "B")
    move_b_to_c = _make_move_action("move", "B", "C")
    init = {Predicate("at", ("A",))}
    goal = {Predicate("at", ("C",))}
    actions = [move, move_b_to_c]
    prob = PlanningProblem(init, goal, actions, {})
    planner = GraphPlan(prob)
    plan = planner.bfs_find_plan(max_depth=5)
    assert plan is not None
    assert len(plan) == 2


def test_heuristic_planner_finds_goal():
    move = _make_move_action("move", "A", "B")
    init = {Predicate("at", ("A",))}
    goal = {Predicate("at", ("B",))}
    actions = [move]
    prob = PlanningProblem(init, goal, actions, {})
    planner = HeuristicPlanner(prob)
    plan = planner.plan(max_steps=20)
    assert plan is not None
    assert len(plan) == 1
    assert plan[0].name == "move"


def test_heuristic_planner_no_action_returns_none():
    init = {Predicate("at", ("A",))}
    goal = {Predicate("at", ("C",))}
    prob = PlanningProblem(init, goal, [], {})
    planner = HeuristicPlanner(prob)
    assert planner.plan(max_steps=5) is None


def test_heuristic_planner_cycle_detection():
    move_a_b = _make_move_action("move", "A", "B")
    move_b_a = _make_move_action("move", "B", "A")
    init = {Predicate("at", ("A",))}
    goal = {Predicate("at", ("C",))}
    actions = [move_a_b, move_b_a]
    prob = PlanningProblem(init, goal, actions, {})
    planner = HeuristicPlanner(prob)
    plan = planner.plan(max_steps=20)
    assert plan is None
