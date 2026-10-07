"""Tests for multi-agent OS - expanded coverage."""

from __future__ import annotations

import pytest

from astrovox.agents import Agent, AgentScheduler, Coder, Debugger, DocSearch, Planner, Reviewer, Tester


def test_agent_history_records_tasks():
    agent = Agent(name="a", role="worker", handler=lambda task: "ok")
    task = type("T", (), {"id": "1", "kind": "work", "payload": {}, "status": "pending", "result": None})()
    agent.execute(task)
    assert len(agent.history) == 1


def test_planner_task_ids_unique():
    planner = Planner()
    tasks = planner.plan("goal")
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids))


def test_scheduler_dispatch_fails_without_agents():
    scheduler = AgentScheduler()
    task = type("T", (), {"id": "1", "kind": "work", "payload": {}, "status": "pending", "result": None})()
    completed = scheduler.dispatch(task)
    assert completed.status == "failed"


def test_coder_write_contains_keyword():
    coder = Coder()
    result = coder.write(type("T", (), {"id": "1", "payload": {"goal": "api"}})())
    assert "api" in result


def test_reviewer_review_mentions_id():
    reviewer = Reviewer()
    result = reviewer.review(type("T", (), {"id": "task-42"})())
    assert "task-42" in result


def test_tester_run_mentions_id():
    tester = Tester()
    result = tester.run(type("T", (), {"id": "task-42"})())
    assert "task-42" in result


def test_debugger_debug_mentions_id():
    debugger = Debugger()
    result = debugger.debug(type("T", (), {"id": "task-42"})())
    assert "task-42" in result


def test_doc_search_search_mentions_goal():
    doc = DocSearch()
    task = type("T", (), {"id": "1", "payload": {"goal": "auth"}})()
    result = doc.search(task)
    assert "auth" in result
