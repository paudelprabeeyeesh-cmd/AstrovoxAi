"""Tests for the production-ready multi-agent framework."""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.multi_agent import (
    AgentRole,
    AgentState,
    TaskStatus,
    PermissionLevel,
    AgentCapability,
    AgentHealth,
    AgentMetadata,
    AgentConfig,
    Agent,
    AgentRegistry,
    AgentOrchestrator,
    CollaborationManager,
    PlannerAgent,
    ResearcherAgent,
    CoderAgent,
    ReviewerAgent,
    SecurityAgent,
    AgentTask,
    AgentMessage,
    CollaborationSession,
)


# ============================================================================
# Agent Base Class Tests
# ============================================================================

class TestAgentLifecycle:
    """Test agent lifecycle state transitions."""

    def test_agent_created_in_created_state(self):
        agent = PlannerAgent()
        assert agent.state == AgentState.CREATED

    def test_valid_transition_created_to_initializing(self):
        agent = PlannerAgent()
        assert agent.transition_to(AgentState.INITIALIZING) is True
        assert agent.state == AgentState.INITIALIZING

    def test_invalid_transition_created_to_running(self):
        agent = PlannerAgent()
        assert agent.transition_to(AgentState.RUNNING) is False
        assert agent.state == AgentState.CREATED

    def test_full_lifecycle(self):
        agent = PlannerAgent()
        assert agent.transition_to(AgentState.INITIALIZING) is True
        assert agent.transition_to(AgentState.READY) is True
        assert agent.transition_to(AgentState.RUNNING) is True
        assert agent.transition_to(AgentState.COMPLETED) is True
        assert agent.transition_to(AgentState.READY) is True
        assert agent.transition_to(AgentState.STOPPED) is True

    def test_failed_to_recovery(self):
        agent = PlannerAgent()
        agent.transition_to(AgentState.INITIALIZING)
        agent.transition_to(AgentState.READY)
        agent.transition_to(AgentState.RUNNING)
        agent.transition_to(AgentState.FAILED)
        assert agent.transition_to(AgentState.RECOVERING) is True
        assert agent.transition_to(AgentState.READY) is True


class TestAgentMetadata:
    """Test agent metadata."""

    def test_metadata_creation(self):
        agent = PlannerAgent()
        assert agent.metadata.name == "Planner"
        assert agent.metadata.version == "1.0.0"
        assert len(agent.metadata.capabilities) > 0
        assert agent.metadata.state == AgentState.CREATED

    def test_metadata_capabilities(self):
        agent = CoderAgent()
        cap_names = [c.name for c in agent.metadata.capabilities]
        assert "code_generation" in cap_names
        assert "code_review" in cap_names
        assert "debugging" in cap_names

    def test_metadata_health(self):
        agent = PlannerAgent()
        health = agent.get_health()
        assert health.status == "created"
        assert health.uptime_seconds >= 0


class TestAgentConfig:
    """Test agent configuration."""

    def test_config_creation(self):
        config = AgentConfig(
            name="Test",
            role="test",
            system_prompt="Test prompt",
        )
        assert config.name == "Test"
        assert config.model == "gpt-4"
        assert config.max_retries == 3

    def test_config_from_dict(self):
        config = AgentConfig.from_dict({
            "name": "FromDict",
            "role": "test",
            "system_prompt": "Test",
            "model": "gpt-4o-mini",
        })
        assert config.name == "FromDict"
        assert config.model == "gpt-4o-mini"

    def test_config_from_json(self):
        config = AgentConfig.from_json('{"name": "JSON", "role": "test", "system_prompt": "Test"}')
        assert config.name == "JSON"

    def test_config_to_dict(self):
        config = AgentConfig(name="Dict", role="test", system_prompt="Test")
        data = config.to_dict()
        assert data["name"] == "Dict"
        assert data["model"] == "gpt-4"


# ============================================================================
# Agent Registry Tests
# ============================================================================

class TestAgentRegistry:
    """Test agent registry operations."""

    def test_register_agent(self):
        registry = AgentRegistry()
        agent = PlannerAgent()
        assert registry.register(agent) is True
        assert registry.get(AgentRole.PLANNER) is agent

    def test_unregister_agent(self):
        registry = AgentRegistry()
        agent = PlannerAgent()
        registry.register(agent)
        assert registry.unregister(AgentRole.PLANNER) is True
        assert registry.get(AgentRole.PLANNER) is None

    def test_register_replaces_existing(self):
        registry = AgentRegistry()
        agent1 = PlannerAgent()
        agent2 = PlannerAgent()
        registry.register(agent1)
        registry.register(agent2)
        assert registry.get(AgentRole.PLANNER) is agent2

    def test_find_by_capability(self):
        registry = AgentRegistry()
        registry.register(CoderAgent())
        agents = registry.find_by_capability("code_generation")
        assert len(agents) == 1
        assert agents[0].role == AgentRole.CODER

    def test_list_agents(self):
        registry = AgentRegistry()
        registry.register(PlannerAgent())
        registry.register(ResearcherAgent())
        agents = registry.list_agents()
        assert len(agents) == 2

    def test_health_history(self):
        registry = AgentRegistry()
        agent = PlannerAgent()
        registry.register(agent)
        health = agent.get_health()
        registry.record_health(AgentRole.PLANNER, health)
        history = registry.get_health_history(AgentRole.PLANNER)
        assert len(history) == 1

    def test_get_all_health(self):
        registry = AgentRegistry()
        registry.register(PlannerAgent())
        all_health = registry.get_all_health()
        assert "planner" in all_health


# ============================================================================
# Orchestrator Tests
# ============================================================================

class TestAgentOrchestrator:
    """Test agent orchestrator."""

    def test_default_agents_registered(self):
        orchestrator = AgentOrchestrator()
        assert len(orchestrator.registry.list_agents()) == 5

    def test_submit_task(self):
        orchestrator = AgentOrchestrator()
        task = orchestrator.submit_task(AgentRole.PLANNER, "Test task")
        assert task.id is not None
        assert task.agent_role == "planner"
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_execute_task(self):
        orchestrator = AgentOrchestrator()
        task = AgentTask(
            id="test-123",
            agent_role="planner",
            description="Test",
        )
        result = await orchestrator.execute_task(task)
        assert result.status == TaskStatus.COMPLETED
        assert len(result.result) > 0

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        orchestrator = AgentOrchestrator()
        tasks = [
            AgentTask(id=f"task-{i}", agent_role="planner", description=f"Task {i}")
            for i in range(3)
        ]
        results = await orchestrator.execute_parallel(tasks)
        assert len(results) == 3
        assert all(r.status == TaskStatus.COMPLETED for r in results)

    def test_get_health(self):
        orchestrator = AgentOrchestrator()
        health = orchestrator.get_health()
        assert "planner" in health

    def test_get_analytics(self):
        orchestrator = AgentOrchestrator()
        analytics = orchestrator.get_analytics()
        assert analytics["total_agents"] == 5
        assert len(analytics["agents"]) == 5


# ============================================================================
# Collaboration Manager Tests
# ============================================================================

class TestCollaborationManager:
    """Test collaboration manager."""

    def test_create_session(self):
        manager = CollaborationManager()
        session = manager.create_session("user_1", "Build a web app")
        assert session.id is not None
        assert len(session.tasks) == 5

    def test_get_session(self):
        manager = CollaborationManager()
        session = manager.create_session("user_1", "Test")
        retrieved = manager.get_session(session.id)
        assert retrieved is session

    def test_get_user_sessions(self):
        manager = CollaborationManager()
        manager.create_session("user_1", "Goal 1")
        manager.create_session("user_1", "Goal 2")
        manager.create_session("user_2", "Goal 3")
        sessions = manager.get_user_sessions("user_1")
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_run_session(self):
        manager = CollaborationManager()
        session = manager.create_session("user_1", "Test goal")
        result = await manager.run_session(session.id)
        assert result.status == TaskStatus.COMPLETED


# ============================================================================
# Specialized Agent Tests
# ============================================================================

class TestSpecializedAgents:
    """Test specialized agent implementations."""

    @pytest.mark.asyncio
    async def test_planner_agent(self):
        agent = PlannerAgent()
        task = AgentTask(id="t1", agent_role="planner", description="Plan")
        result = await agent.execute(task, {"goal": "Build app"})
        assert "Plan for:" in result

    @pytest.mark.asyncio
    async def test_researcher_agent(self):
        agent = ResearcherAgent()
        task = AgentTask(id="t1", agent_role="researcher", description="Research")
        result = await agent.execute(task, {})
        assert "Research findings" in result

    @pytest.mark.asyncio
    async def test_coder_agent(self):
        agent = CoderAgent()
        task = AgentTask(id="t1", agent_role="coder", description="Code")
        result = await agent.execute(task, {})
        assert "Code implementation" in result

    @pytest.mark.asyncio
    async def test_reviewer_agent(self):
        agent = ReviewerAgent()
        task = AgentTask(id="t1", agent_role="reviewer", description="Review")
        result = await agent.execute(task, {})
        assert "Review of:" in result

    @pytest.mark.asyncio
    async def test_security_agent(self):
        agent = SecurityAgent()
        task = AgentTask(id="t1", agent_role="security", description="Security")
        result = await agent.execute(task, {})
        assert "Security review" in result
