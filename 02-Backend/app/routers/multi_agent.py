import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["multi-agent"])


@router.post("/agents/multi/orchestrate")
async def orchestrate_agents(req: dict, user_id: str = Depends(require_verified_email)):
    task = req.get("task", "")
    num_agents = req.get("num_agents", 3)
    sub_task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO agent_orchestrations (id, user_id, main_task, num_agents, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sub_task_id, user_id, task, num_agents, "starting", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    agents = []
    for i in range(num_agents):
        agent_id = str(uuid.uuid4())
        agent_name = f"sub-agent-{i+1}"
        agent_role = req.get("roles", {}).get(agent_name, f"Executing sub-task {i+1}")
        agents.append({
            "id": agent_id,
            "name": agent_name,
            "role": agent_role,
            "status": "queued",
        })
    with get_db() as conn:
        for agent in agents:
            conn.execute(
                "INSERT INTO agent_tasks (id, orchestration_id, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (agent["id"], sub_task_id, agent["name"], agent["role"], "queued", datetime.now(timezone.utc).isoformat()),
            )
        conn.commit()
    return {"orchestration_id": sub_task_id, "task": task, "agents": agents, "status": "starting"}


@router.get("/agents/multi/{orchestration_id}")
async def get_orchestration(orchestration_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, main_task, num_agents, status, created_at FROM agent_orchestrations WHERE id = ? AND user_id = ?",
            (orchestration_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Orchestration not found")
        tasks = conn.execute(
            "SELECT id, name, role, status, result FROM agent_tasks WHERE orchestration_id = ?",
            (orchestration_id,),
        ).fetchall()
        result = dict(row)
        result["tasks"] = [dict(t) for t in tasks]
        return result


@router.post("/agents/multi/{orchestration_id}/delegate")
async def delegate_subtask(req: dict, orchestration_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM agent_orchestrations WHERE id = ? AND user_id = ?",
            (orchestration_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Orchestration not found")
        task_id = str(uuid.uuid4())
        sub_task = req.get("task", "")
        assigned_agent = req.get("assigned_agent", "any")
        conn.execute(
            "INSERT INTO agent_tasks (id, orchestration_id, name, role, status, assigned_to, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, orchestration_id, sub_task, "subtask", "queued", assigned_agent, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"task_id": task_id, "task": sub_task, "assigned_to": assigned_agent}


@router.get("/agents/multi")
async def list_orchestrations(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, main_task, num_agents, status, created_at FROM agent_orchestrations WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["created_at"] = item["created_at"]
            result.append(item)
        return result
