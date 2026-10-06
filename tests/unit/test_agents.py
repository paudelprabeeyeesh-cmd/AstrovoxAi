"""Tests for multi-agent operating system."""

from __future__ import annotations

import pytest

from astrovox.agents import Agent, AgentScheduler, Coder, Debugger, DocSearch, Planner, Reviewer, Tester


def test_planner_creates_tasks():
    planner = Planner()
    tasks = planner.plan("build web app")
    assert len(tasks) == 5
    assert tasks[0].kind == "search_docs"


def test_coder_generates_implementation():
    coder = Coder()
    result = coder.write(type("T", (), {"id": "1", "payload": {"goal": "app"}})())
    assert "Implementation" in result


def test_reviewer_returns_review():
    reviewer = Reviewer()
    result = reviewer.review(type("T", (), {"id": "1"})())
    assert "reviewed" in result


def test_tester_reports_pass():
    tester = Tester()
    result = tester.run(type("T", (), {"id": "1"})())
    assert "passed" in result


def test_debugger_reports_debug():
    debugger = Debugger()
    result = debugger.debug(type("T", (), {"id": "1"})())
    assert "debugged" in result


def test_doc_search_returns_docs():
    doc = DocSearch()
    result = doc.search(type("T", (), {"payload": {"goal": "app"}})())
    assert "docs" in result


def test_agent_scheduler_dispatches_task():
    scheduler = AgentScheduler()
    scheduler.register(Agent(name="a", role="worker", handler=lambda task: "ok"))
    task = type("T", (), {"id": "1", "kind": "work", "payload": {}, "status": "pending", "result": None})()
    completed = scheduler.dispatch(task)
    assert completed.status == "completed"
    assert completed.result == "ok"
