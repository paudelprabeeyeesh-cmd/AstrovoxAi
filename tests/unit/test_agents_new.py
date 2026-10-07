"""Tests for multi-agent OS - expanded coverage."""

from __future__ import annotations

import threading

import pytest

from astrovox.agents import Agent, AgentScheduler, Coder, Debugger, DocSearch, Planner, Reviewer, Tester


def test_planner_plan_returns_five_tasks():
    planner = Planner()
    tasks = planner.plan("anything")
    assert len(tasks) == 5
    kinds = [t.kind for t in tasks]
    assert kinds == ["search_docs", "write_code", "review_code", "run_tests", "debug"]


def test_agent_execute_returns_task_with_result():
    agent = Agent(name="worker", role="worker", handler=lambda task: "done")
    task = type("T", (), {"id": "1", "kind": "work", "payload": {}, "status": "pending", "result": None})()
    completed = agent.execute(task)
    assert completed.result == "done"
    assert completed.status == "completed"


def test_scheduler_registers_multiple_agents():
    scheduler = AgentScheduler()
    scheduler.register(Agent(name="a1", role="worker", handler=lambda t: "a1"))
    scheduler.register(Agent(name="a2", role="worker", handler=lambda t: "a2"))
    assert len(scheduler.agents) == 2


def test_coder_write_returns_string():
    coder = Coder()
    result = coder.write(type("T", (), {"id": "1", "payload": {"goal": "api"}})())
    assert isinstance(result, str)


def test_reviewer_review_returns_string():
    reviewer = Reviewer()
    result = reviewer.review(type("T", (), {"id": "1"})())
    assert isinstance(result, str)
