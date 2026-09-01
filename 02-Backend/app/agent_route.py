"""AI Agent API routes — autonomous task execution."""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from typing import Optional

from .agent import agent_manager
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/agent", tags=["agent"])


class CreateTaskRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=1000)


class ExecuteTaskRequest(BaseModel):
    task_id: str


@router.post("/tasks")
async def create_task(request: CreateTaskRequest, authorization: str = Header(None)):
    """Create a new agent task."""
    user_id = get_user_id_from_token(authorization)
    agent = agent_manager.get_agent(user_id)

    task = await agent.create_task(request.goal)

    return {
        "status": "OK",
        "task": {
            "id": task.id,
            "goal": task.goal,
            "state": task.state.value,
            "steps": [
                {
                    "step_number": s.step_number,
                    "action": s.action,
                    "description": s.description,
                    "status": s.status,
                }
                for s in task.steps
            ],
        },
    }


@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, authorization: str = Header(None)):
    """Execute an agent task."""
    user_id = get_user_id_from_token(authorization)
    agent = agent_manager.get_agent(user_id)

    try:
        task = await agent.execute_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return {
        "status": "OK",
        "task": {
            "id": task.id,
            "goal": task.goal,
            "state": task.state.value,
            "result": task.result,
            "steps": [
                {
                    "step_number": s.step_number,
                    "action": s.action,
                    "description": s.description,
                    "status": s.status,
                    "result": s.result,
                }
                for s in task.steps
            ],
        },
    }


@router.get("/tasks")
async def list_tasks(authorization: str = Header(None)):
    """List all agent tasks."""
    user_id = get_user_id_from_token(authorization)
    agent = agent_manager.get_agent(user_id)
    tasks = agent.get_all_tasks()

    return {
        "status": "OK",
        "tasks": [
            {
                "id": t.id,
                "goal": t.goal,
                "state": t.state.value,
                "step_count": len(t.steps),
                "current_step": t.current_step,
            }
            for t in tasks
        ],
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, authorization: str = Header(None)):
    """Get task details."""
    user_id = get_user_id_from_token(authorization)
    agent = agent_manager.get_agent(user_id)
    task = agent.get_task(task_id)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return {
        "status": "OK",
        "task": {
            "id": task.id,
            "goal": task.goal,
            "state": task.state.value,
            "result": task.result,
            "steps": [
                {
                    "step_number": s.step_number,
                    "action": s.action,
                    "description": s.description,
                    "status": s.status,
                    "result": s.result,
                }
                for s in task.steps
            ],
        },
    }


@router.get("/tools")
async def list_tools(authorization: str = Header(None)):
    """List available agent tools."""
    user_id = get_user_id_from_token(authorization)
    agent = agent_manager.get_agent(user_id)

    return {"status": "OK", "tools": agent.tools.list_tools()}
