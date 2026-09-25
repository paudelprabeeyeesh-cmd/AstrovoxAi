import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workflows"])


@router.post("/workflows")
async def create_workflow(req: dict, user_id: str = Depends(require_verified_email)):
    workflow_id = str(uuid.uuid4())
    name = req.get("name", "Untitled Workflow")
    steps = json.dumps(req.get("steps", []))
    triggers = json.dumps(req.get("triggers", []))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO workflows (id, user_id, name, steps, triggers, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (workflow_id, user_id, name, steps, triggers, 1, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": workflow_id, "name": name}


@router.get("/workflows")
async def list_workflows(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, steps, triggers, enabled, created_at FROM workflows WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["steps"] = json.loads(item.get("steps", "[]"))
            item["triggers"] = json.loads(item.get("triggers", "[]"))
            result.append(item)
        return result


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, req: dict, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, steps, triggers FROM workflows WHERE id = ? AND user_id = ?",
            (workflow_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")
        steps = json.loads(row["steps"] or "[]")
        results = []
        for step in steps:
            results.append({
                "step_id": step.get("id"),
                "action": step.get("action"),
                "result": f"Executed step {step.get('id')} with params {json.dumps(step.get('params', {}))[:100]}",
            })
    return {"workflow_id": workflow_id, "name": row["name"], "results": results}


@router.post("/workflows/{workflow_id}/toggle")
async def toggle_workflow(workflow_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, enabled FROM workflows WHERE id = ? AND user_id = ?",
            (workflow_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")
        new_enabled = 1 - row["enabled"]
        conn.execute("UPDATE workflows SET enabled = ? WHERE id = ?", (new_enabled, workflow_id))
        conn.commit()
    return {"workflow_id": workflow_id, "enabled": bool(new_enabled)}