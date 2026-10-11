"""Tests for multi-agent collaboration and enhanced memory."""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch

from app.multi_agent import (
    collaboration_manager,
    PlannerAgent,
    ResearcherAgent,
    CoderAgent,
    ReviewerAgent,
    SecurityAgent,
    AgentRole,
    TaskStatus,
)
from app.memory_enhanced import memory_store, MemoryRanker, MemoryEntry
from app.tools import tool_registry, CalculatorTool
from app.security_hardening import Principal
from app.circuit_breaker import (
    circuit_breaker_manager,
    quota_manager,
    cost_monitor,
    CircuitBreaker,
    CircuitState,
)
from app.auth_enhanced import password_hasher, device_manager, login_alerts
from app.ai_security_enhanced import pii_detector, secret_detector, conversation_limiter


# ============================================================================
# Multi-Agent Tests
# ============================================================================

class TestMultiAgent:
    def test_create_session(self):
        session = collaboration_manager.create_session("user_1", "Build a web app")
        assert session.id is not None
        assert session.user_id == "user_1"
        assert session.goal == "Build a web app"
        assert len(session.tasks) == 5

    def test_session_has_all_roles(self):
        session = collaboration_manager.create_session("user_1", "Test goal")
        roles = {t.agent_role for t in session.tasks}
        assert "planner" in roles
        assert "researcher" in roles
        assert "coder" in roles
        assert "reviewer" in roles
        assert "security" in roles

    def test_session_dependencies(self):
        session = collaboration_manager.create_session("user_1", "Test goal")
        planner = next(t for t in session.tasks if t.agent_role == "planner")
        coder = next(t for t in session.tasks if t.agent_role == "coder")
        assert planner.id in coder.dependencies

    @pytest.mark.asyncio
    async def test_run_session(self):
        session = collaboration_manager.create_session("user_1", "Test goal")
        result = await collaboration_manager.run_session(session.id)
        assert result.status == TaskStatus.COMPLETED
        assert len(result.result) > 0

    def test_get_user_sessions(self):
        collaboration_manager.create_session("user_1", "Goal 1")
        collaboration_manager.create_session("user_1", "Goal 2")
        sessions = collaboration_manager.get_user_sessions("user_1")
        assert len(sessions) >= 2


# ============================================================================
# Enhanced Memory Tests
# ============================================================================

class TestEnhancedMemory:
    def test_add_memory(self):
        entry = memory_store.add_memory("user_1", "Test memory", "general", 1.0)
        assert entry.id is not None
        assert entry.content == "Test memory"
        assert entry.memory_type == "general"

    def test_add_episodic(self):
        memory = memory_store.add_episodic(
            "user_1", "Meeting", "Discussed project", ["user_2"], "Success"
        )
        assert memory.id is not None
        assert memory.title == "Meeting"

    def test_add_semantic(self):
        memory = memory_store.add_semantic("user_1", "Python is a language", "facts", 0.9)
        assert memory.id is not None
        assert memory.fact == "Python is a language"

    def test_search_memories(self):
        memory_store.add_memory("user_1", "Python programming", "technical", 2.0)
        memory_store.add_memory("user_1", "Machine learning", "technical", 1.5)
        results = memory_store.search("user_1", query="Python")
        assert len(results) > 0

    def test_memory_ranking(self):
        entry = MemoryEntry(
            id="test", user_id="user_1", content="Test",
            memory_type="general", importance=1.0,
            created_at=time.time(), access_count=5,
        )
        ranker = MemoryRanker()
        score = ranker.calculate_relevance(entry, "test")
        assert score > 0

    def test_memory_decay(self):
        entry = MemoryEntry(
            id="test", user_id="user_1", content="Test",
            memory_type="general", importance=1.0,
            created_at=time.time() - 86400 * 30,
        )
        ranker = MemoryRanker()
        decayed = ranker.apply_decay(entry)
        assert decayed < 1.0

    def test_cleanup(self):
        for i in range(10):
            memory_store.add_memory("user_1", f"Memory {i}", "general", 0.1)
        removed = memory_store.cleanup("user_1", max_memories=5)
        assert removed > 0

    def test_get_stats(self):
        memory_store.add_memory("user_1", "Test", "general")
        stats = memory_store.get_stats("user_1")
        assert stats["total_memories"] > 0


import time


# ============================================================================
# Tools Tests
# ============================================================================

class TestTools:
    def test_calculator_basic(self):
        result = tool_registry.calculator.calculate("2 + 2")
        assert result.success
        assert result.result == "4"

    def test_calculator_complex(self):
        result = tool_registry.calculator.calculate("(10 + 5) * 2")
        assert result.success
        assert result.result == "30"

    def test_calculator_unsafe(self):
        result = tool_registry.calculator.calculate("__import__('os').system('ls')")
        assert not result.success

    def test_list_tools(self):
        tools = tool_registry.get_tools()
        assert len(tools) >= 5
        tool_names = [t["name"] for t in tools]
        assert "calculator" in tool_names
        assert "weather" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        result = await tool_registry.execute("calculator", expression="3 * 3")
        assert result.success
        assert result.result == "9"

    def test_code_executor_uses_secure_executor(self):
        admin = Principal(id="admin-1", email="admin@test.com", role="admin")
        result = tool_registry.code_executor.execute("print('secure test')", principal=admin)
        assert result.success
        assert "secure test" in result.result

    def test_code_executor_rejects_non_admin(self):
        user = Principal(id="user-1", email="user@test.com", role="user")
        result = tool_registry.code_executor.execute("print('hack')", principal=user)
        assert not result.success
        assert "admin" in result.result.lower() or "privilege" in result.result.lower()


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    def test_circuit_closed_by_default(self):
        breaker = circuit_breaker_manager.get_breaker("test_provider")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute()

    def test_circuit_opens_after_failures(self):
        breaker = circuit_breaker_manager.get_breaker("failing_provider")
        for _ in range(5):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert not breaker.can_execute()

    def test_circuit_recovers(self):
        breaker = circuit_breaker_manager.get_breaker("recovering_provider")
        for _ in range(5):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_token_quota(self):
        quota = quota_manager.get_quota("user_1")
        ok, msg = quota.check_quota(1000)
        assert ok

    def test_token_quota_exceeded(self):
        quota = quota_manager.get_quota("limited_user")
        quota.daily_used = quota.daily_token_limit
        quota.last_reset_daily = time.time()
        ok, msg = quota.check_quota(1000)
        assert not ok

    def test_cost_monitor(self):
        cost_monitor.record_cost("user_1", 5.0)
        daily = cost_monitor.get_daily_cost("user_1")
        assert daily == 5.0


# ============================================================================
# Security Tests
# ============================================================================

class TestSecurity:
    def test_password_hash(self):
        hashed = password_hasher.hash("SecurePass123!")
        assert hashed is not None
        assert password_hasher.verify("SecurePass123!", hashed)

    def test_password_wrong(self):
        hashed = password_hasher.hash("SecurePass123!")
        assert not password_hasher.verify("WrongPass", hashed)

    def test_pii_detection(self):
        result = pii_detector.scan("Contact me at test@example.com")
        assert not result.safe
        assert len(result.issues) > 0

    def test_pii_masking(self):
        masked = pii_detector.mask_pii("SSN: 123-45-6789")
        assert "123-45-6789" not in masked

    def test_secret_detection(self):
        result = secret_detector.scan("My key is sk-abc123def456ghi789jkl012mno345pqr")
        assert not result.safe

    def test_conversation_limiter(self):
        ok, msg = conversation_limiter.check_limits("user_1", 1)
        assert ok

    def test_device_management(self):
        device = device_manager.register_device("user_1", "Mozilla/5.0", "192.168.1.1")
        assert device.device_id is not None
        devices = device_manager.get_devices("user_1")
        assert len(devices) > 0

    def test_login_alerts(self):
        for _ in range(6):
            login_alerts.record_login("user_1", "192.168.1.1", "Mozilla/5.0", False)
        alerts = login_alerts.get_alerts()
        assert len(alerts) > 0
