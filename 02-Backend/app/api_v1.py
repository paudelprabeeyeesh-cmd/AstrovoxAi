"""Comprehensive API Layer for Agent Management and Workflow Execution.

Provides endpoints for:
- Agent management (register, unregister, list, configure)
- Workflow execution (start, stop, pause, resume)
- Workflow templates (create, list, clone)
- Task status and history
- Agent metrics and analytics
- Agent configuration
"""

import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from .auth_utils import get_user_id_from_token
from .multi_agent import agent_orchestrator, CollaborationManager
from .workflow_engine import workflow_engine, WorkflowStep, StepAction
from .tool_execution import tool_executor
from .dashboard import dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["v1-api"])


# ============================================================================
# Request Models
# ============================================================================

class AgentConfigRequest(BaseModel):
    name: str
    role: str
    system_prompt: str
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    steps: list[dict] = []


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str
    triggered_by: str = "manual"


class TaskCancelRequest(BaseModel):
    task_id: str


# ============================================================================
# Agent Management Endpoints
# ============================================================================

@router.get("/agents")
async def list_agents(authorization: str = Header(None)):
    """List all registered agents with their status."""
    user_id = get_user_id_from_token(authorization)
    analytics = agent_orchestrator.get_analytics()
    return {"status": "OK", "agents": analytics.get("agents", [])}


@router.get("/agents/{role}")
async def get_agent(role: str, authorization: str = Header(None)):
    """Get detailed information about a specific agent."""
    user_id = get_user_id_from_token(authorization)

    from .multi_agent import AgentRole
    try:
        agent_role = AgentRole(role)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    agent = agent_orchestrator.registry.get(agent_role)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {role}")

    return {
        "status": "OK",
        "agent": {
            "name": agent.config.name,
            "role": agent.role.value,
            "state": agent.state.value,
            "capabilities": [c.name for c in agent.metadata.capabilities],
            "health": agent.get_health().__dict__,
        },
    }


@router.get("/agents/{role}/health")
async def get_agent_health(role: str, authorization: str = Header(None)):
    """Get health metrics for a specific agent."""
    user_id = get_user_id_from_token(authorization)
    health = agent_orchestrator.get_health()
    if role not in health:
        raise HTTPException(status_code=404, detail=f"Agent not found: {role}")
    return {"status": "OK", "health": health[role].__dict__}


# ============================================================================
# Workflow Endpoints
# ============================================================================

@router.post("/workflows")
async def create_workflow(request: WorkflowCreateRequest, authorization: str = Header(None)):
    """Create a new workflow."""
    user_id = get_user_id_from_token(authorization)
    wf = workflow_engine.create_workflow(request.name, request.description)

    for step_data in request.steps:
        workflow_engine.add_step(
            wf.id,
            step_data.get("name", "Step"),
            StepAction(step_data.get("action", "agent_task")),
            step_data.get("config", {}),
            step_data.get("dependencies", []),
        )

    return {
        "status": "OK",
        "workflow": {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "steps": len(wf.steps),
        },
    }


@router.get("/workflows")
async def list_workflows(authorization: str = Header(None)):
    """List all workflows."""
    user_id = get_user_id_from_token(authorization)
    workflows = workflow_engine.list_workflows()
    return {
        "status": "OK",
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "status": w.status,
                "steps": len(w.steps),
                "run_count": w.run_count,
            }
            for w in workflows
        ],
    }


@router.get("/workflows/templates")
async def list_templates(authorization: str = Header(None)):
    """List workflow templates."""
    user_id = get_user_id_from_token(authorization)
    templates = workflow_engine.list_templates()
    return {
        "status": "OK",
        "templates": [
            {"id": t.id, "name": t.name, "steps": len(t.steps)}
            for t in templates
        ],
    }


@router.post("/workflows/templates")
async def create_template(request: WorkflowCreateRequest, authorization: str = Header(None)):
    """Create a workflow template."""
    user_id = get_user_id_from_token(authorization)
    template = workflow_engine.create_template(request.name, request.description)

    for step_data in request.steps:
        workflow_engine.add_step(
            template.id,
            step_data.get("name", "Step"),
            StepAction(step_data.get("action", "agent_task")),
            step_data.get("config", {}),
        )

    return {
        "status": "OK",
        "template": {"id": template.id, "name": template.name},
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, authorization: str = Header(None)):
    """Get workflow details."""
    user_id = get_user_id_from_token(authorization)
    wf = workflow_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "status": "OK",
        "workflow": {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "status": wf.status,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "action": s.action.value,
                    "status": s.status,
                }
                for s in wf.steps
            ],
        },
    }


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, authorization: str = Header(None)):
    """Execute a workflow."""
    user_id = get_user_id_from_token(authorization)
    execution = await workflow_engine.execute_workflow(workflow_id)

    return {
        "status": "OK",
        "execution": {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "step_results": execution.step_results,
        },
    }


@router.post("/workflows/clone/{template_id}")
async def clone_workflow(template_id: str, name: str = "", authorization: str = Header(None)):
    """Clone a workflow template."""
    user_id = get_user_id_from_token(authorization)
    clone = workflow_engine.clone_workflow(template_id, name)
    if not clone:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "status": "OK",
        "workflow": {"id": clone.id, "name": clone.name},
    }


# ============================================================================
# Execution Endpoints
# ============================================================================

@router.get("/executions")
async def list_executions(authorization: str = Header(None)):
    """List workflow executions."""
    user_id = get_user_id_from_token(authorization)
    executions = list(workflow_engine._executions.values())
    return {
        "status": "OK",
        "executions": [
            {
                "id": e.id,
                "workflow_id": e.workflow_id,
                "status": e.status.value,
                "started_at": e.started_at,
                "completed_at": e.completed_at,
            }
            for e in executions
        ],
    }


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, authorization: str = Header(None)):
    """Get execution details."""
    user_id = get_user_id_from_token(authorization)
    execution = workflow_engine._executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {
        "status": "OK",
        "execution": {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "step_results": execution.step_results,
            "errors": execution.errors,
        },
    }


# ============================================================================
# Tool Endpoints
# ============================================================================

@router.get("/tools")
async def list_tools(authorization: str = Header(None)):
    """List all available tools."""
    user_id = get_user_id_from_token(authorization)
    tools = tool_executor.registry.list_tools()
    return {"status": "OK", "tools": tools}


@router.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, params: dict = None, authorization: str = Header(None)):
    """Execute a tool with security controls."""
    user_id = get_user_id_from_token(authorization)
    result = await tool_executor.execute(
        tool_name,
        user_id,
        params=params or {},
    )
    return {"status": "OK" if result["success"] else "ERROR", **result}


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/agents")
async def get_agent_analytics(authorization: str = Header(None)):
    """Get agent performance analytics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **agent_orchestrator.get_analytics()}


@router.get("/analytics/tools")
async def get_tool_analytics(authorization: str = Header(None)):
    """Get tool execution analytics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "metrics": tool_executor.get_metrics()}


@router.get("/analytics/workflows")
async def get_workflow_analytics(authorization: str = Header(None)):
    """Get workflow analytics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **workflow_engine.get_analytics()}


# ============================================================================
# Collaboration Endpoints
# ============================================================================

@router.post("/collaborations")
async def create_collaboration(goal: str, authorization: str = Header(None)):
    """Create a new collaboration session."""
    user_id = get_user_id_from_token(authorization)
    session = collaboration_manager.create_session(user_id, goal)
    return {
        "status": "OK",
        "session": {
            "id": session.id,
            "goal": session.goal,
            "tasks": len(session.tasks),
        },
    }


@router.get("/collaborations")
async def list_collaborations(authorization: str = Header(None)):
    """List user's collaboration sessions."""
    user_id = get_user_id_from_token(authorization)
    sessions = collaboration_manager.get_user_sessions(user_id)
    return {
        "status": "OK",
        "sessions": [
            {
                "id": s.id,
                "goal": s.goal,
                "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                "created_at": s.created_at,
            }
            for s in sessions
        ],
    }


@router.get("/collaborations/{session_id}")
async def get_collaboration(session_id: str, authorization: str = Header(None)):
    """Get collaboration session details."""
    user_id = get_user_id_from_token(authorization)
    session = collaboration_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "OK",
        "session": {
            "id": session.id,
            "goal": session.goal,
            "status": session.status.value if hasattr(session.status, "value") else str(session.status),
            "result": session.result,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                    "result": t.result,
                }
                for t in session.tasks
            ],
        },
    }


@router.post("/collaborations/{session_id}/run")
async def run_collaboration(session_id: str, authorization: str = Header(None)):
    """Run a collaboration session."""
    user_id = get_user_id_from_token(authorization)
    session = await collaboration_manager.run_session(session_id)
    return {
        "status": "OK",
        "session": {
            "id": session.id,
            "status": session.status.value if hasattr(session.status, "value") else str(session.status),
            "result": session.result,
        },
    }


# Import collaboration manager at module level
from .multi_agent import collaboration_manager
