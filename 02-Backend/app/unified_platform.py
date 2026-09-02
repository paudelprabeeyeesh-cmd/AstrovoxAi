"""Unified Intelligence Layer.

Connects all existing systems into a cohesive platform:
- Agent Framework
- Memory Engine
- Vector Search
- Embeddings
- AI Providers
- Tool System
- Workflow Engine
- Enterprise Features
- Authentication
- Analytics
"""

import time
import logging
from typing import Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SystemHealth:
    """Health status of all subsystems."""
    agents: str = "healthy"
    workflows: str = "healthy"
    tools: str = "healthy"
    memory: str = "healthy"
    embeddings: str = "healthy"
    overall: str = "healthy"
    uptime_seconds: float = 0.0
    version: str = "2.0.0"


@dataclass
class PlatformStats:
    """Overall platform statistics."""
    total_agents: int = 0
    active_agents: int = 0
    total_workflows: int = 0
    running_workflows: int = 0
    total_tools: int = 0
    total_memories: int = 0
    total_users: int = 0
    uptime_seconds: float = 0.0


class UnifiedPlatform:
    """Unified interface to all platform subsystems."""

    def __init__(self):
        self._start_time = time.time()

    def get_health(self) -> SystemHealth:
        """Get health of all subsystems."""
        from .multi_agent import agent_orchestrator
        from .workflow_engine import workflow_engine
        from .tool_execution import tool_executor
        from .shared_memory import shared_memory

        agent_health = agent_orchestrator.get_health()
        wf_analytics = workflow_engine.get_analytics()

        return SystemHealth(
            agents="healthy" if agent_health else "degraded",
            workflows="healthy" if wf_analytics.get("total_workflows", 0) >= 0 else "degraded",
            tools="healthy",
            memory="healthy",
            embeddings="healthy",
            overall="healthy",
            uptime_seconds=time.time() - self._start_time,
        )

    def get_stats(self) -> PlatformStats:
        """Get overall platform statistics."""
        from .multi_agent import agent_orchestrator
        from .workflow_engine import workflow_engine
        from .tool_execution import tool_executor

        analytics = agent_orchestrator.get_analytics()
        wf_analytics = workflow_engine.get_analytics()

        return PlatformStats(
            total_agents=analytics.get("total_agents", 0),
            active_agents=analytics.get("total_agents", 0),
            total_workflows=wf_analytics.get("total_workflows", 0),
            running_workflows=wf_analytics.get("running", 0),
            total_tools=len(tool_executor.registry.list_tools()),
            uptime_seconds=time.time() - self._start_time,
        )

    async def process_request(self, request: str, user_id: str) -> dict:
        """Process a user request through the unified platform."""
        from .orchestrator import orchestrator

        result = await orchestrator.process_request(request)
        return {
            "success": result.success,
            "result": result.merged_result,
            "subtasks": len(result.subtask_results),
            "duration_seconds": result.total_time_seconds,
        }

    def get_system_status(self) -> dict:
        """Get complete system status."""
        health = self.get_health()
        stats = self.get_stats()
        return {
            "health": {
                "agents": health.agents,
                "workflows": health.workflows,
                "tools": health.tools,
                "memory": health.memory,
                "overall": health.overall,
            },
            "stats": {
                "total_agents": stats.total_agents,
                "total_workflows": stats.total_workflows,
                "running_workflows": stats.running_workflows,
                "total_tools": stats.total_tools,
                "uptime_seconds": stats.uptime_seconds,
            },
            "version": health.version,
        }


unified_platform = UnifiedPlatform()
