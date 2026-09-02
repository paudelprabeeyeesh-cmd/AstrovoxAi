"""Tests for the agent orchestration engine."""

import pytest
from app.orchestrator import (
    TaskAnalyzer,
    AgentSelector,
    ResultMerger,
    Orchestrator,
    ExecutionMode,
    ExecutionPlan,
    ExecutionResult,
    Subtask,
)
from app.multi_agent import AgentRole


class TestTaskAnalyzer:
    def test_analyze_research_request(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Research AI safety")
        roles = [t.agent_role for t in subtasks]
        assert "researcher" in roles
        assert "reviewer" in roles

    def test_analyze_code_request(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Build a web app with Python")
        roles = [t.agent_role for t in subtasks]
        assert "coder" in roles

    def test_analyze_security_request(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Security scan my code")
        roles = [t.agent_role for t in subtasks]
        assert "security" in roles

    def test_analyze_planning_request(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Plan the architecture")
        roles = [t.agent_role for t in subtasks]
        assert "planner" in roles

    def test_analyze_default_request(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Hello world")
        assert len(subtasks) > 0
        roles = [t.agent_role for t in subtasks]
        assert "planner" in roles

    def test_reviewer_always_included(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Simple task")
        roles = [t.agent_role for t in subtasks]
        assert "reviewer" in roles

    def test_dependencies_set_for_reviewer(self):
        analyzer = TaskAnalyzer()
        subtasks = analyzer.analyze("Research and code")
        reviewer = next(t for t in subtasks if t.agent_role == "reviewer")
        assert len(reviewer.dependencies) > 0


class TestAgentSelector:
    def test_select_researcher(self):
        role = AgentSelector.select("Research the latest AI trends")
        assert role == AgentRole.RESEARCHER

    def test_select_coder(self):
        role = AgentSelector.select("Implement a REST API")
        assert role == AgentRole.CODER

    def test_select_reviewer(self):
        role = AgentSelector.select("Review my code")
        assert role == AgentRole.REVIEWER

    def test_select_security(self):
        role = AgentSelector.select("Check for vulnerabilities")
        assert role == AgentRole.SECURITY

    def test_select_planner(self):
        role = AgentSelector.select("Design the system architecture")
        assert role == AgentRole.PLANNER

    def test_select_default(self):
        role = AgentSelector.select("Hello world")
        assert role == AgentRole.RESEARCHER


class TestResultMerger:
    def test_merge_results(self):
        merger = ResultMerger()
        results = [
            {"role": "planner", "result": "Plan created"},
            {"role": "coder", "result": "Code written"},
        ]
        merged = merger.merge(results)
        assert "# Results" in merged
        assert "Planner Output" in merged
        assert "Coder Output" in merged

    def test_merge_empty_results(self):
        merger = ResultMerger()
        merged = merger.merge([])
        assert "No results" in merged


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_process_request(self):
        orch = Orchestrator()
        result = await orch.process_request("Research AI safety")
        assert result.success
        assert len(result.subtask_results) > 0
        assert result.total_time_seconds >= 0

    @pytest.mark.asyncio
    async def test_process_request_parallel(self):
        orch = Orchestrator()
        result = await orch.process_request("Build app", mode=ExecutionMode.PARALLEL)
        assert result.success

    @pytest.mark.asyncio
    async def test_process_request_sequential(self):
        orch = Orchestrator()
        result = await orch.process_request("Plan project", mode=ExecutionMode.SEQUENTIAL)
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_plan(self):
        orch = Orchestrator()
        plan = ExecutionPlan(id="test-plan", goal="Test")
        orch._plans["test-plan"] = plan
        result = await orch.execute_plan("test-plan")
        assert isinstance(result, ExecutionResult)

    def test_get_plan(self):
        orch = Orchestrator()
        plan = ExecutionPlan(id="test", goal="Test")
        orch._plans["test"] = plan
        assert orch.get_plan("test") is plan

    def test_get_plan_not_found(self):
        orch = Orchestrator()
        assert orch.get_plan("nonexistent") is None

    def test_get_analytics(self):
        orch = Orchestrator()
        analytics = orch.get_analytics()
        assert "total_plans" in analytics
        assert "agent_health" in analytics
        assert "agent_analytics" in analytics
