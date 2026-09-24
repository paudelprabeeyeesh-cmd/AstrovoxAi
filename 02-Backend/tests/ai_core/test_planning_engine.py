import numpy as np
import pytest
from ai_core.planning_engine import PlanningEngine, StateSpacePlanner, HierarchicalGoalNetwork, State, Action


def make_actions():
    return [
        Action(name="move", preconditions={"at": "A"}, effects={"at": "B"}, cost=1.0),
        Action(name="move", preconditions={"at": "B"}, effects={"at": "C"}, cost=1.0),
    ]


def test_state_space_planner_finds_path():
    planner = StateSpacePlanner()
    start = State(id="s0", data={"at": "A"})
    goal = State(id="g", data={"at": "C"})
    actions = make_actions()
    plan = planner.plan(start, goal, actions)
    assert len(plan) == 2
    assert plan[0].name == "move"


def test_state_space_planner_no_path():
    planner = StateSpacePlanner()
    start = State(id="s0", data={"at": "A"})
    goal = State(id="g", data={"at": "Z"})
    actions = make_actions()
    plan = planner.plan(start, goal, actions)
    assert plan == []


def test_hierarchical_goal_topo_order():
    net = HierarchicalGoalNetwork()
    net.add_goal("g1", "first")
    net.add_goal("g2", "second")
    net.add_dependency("g2", "g1")
    order = net.topo_order()
    assert order.index("g1") < order.index("g2")


def test_hierarchical_goal_execution_sequence():
    net = HierarchicalGoalNetwork()
    net.add_goal("g1", "low", priority=1.0)
    net.add_goal("g2", "high", priority=10.0)
    seq = net.get_execution_sequence()
    assert seq.index("g2") < seq.index("g1")


def test_planning_engine_integration():
    engine = PlanningEngine()
    engine.define_goal("goal1", "reach destination")
    engine.add_dependency("goal1", "setup")
    start = State(id="start", data={"at": "A"})
    goal = State(id="goal", data={"at": "C"})
    actions = make_actions()
    plan = engine.plan_actions(start, goal, actions)
    assert len(plan) == 2
    assert len(engine.get_plan_history()) == 1
