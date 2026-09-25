import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


@router.post("/skills")
async def create_skill(skill: dict, user_id: str = Depends(require_verified_email)):
    skill_id = str(uuid.uuid4())
    name = skill.get("name", "Untitled")
    description = skill.get("description", "")
    version = skill.get("version", "1.0.0")
    tools = json.dumps(skill.get("tools", []))
    prompts = json.dumps(skill.get("prompts", {}))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO agent_skills (id, user_id, name, description, version, tools, prompts, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (skill_id, user_id, name, description, version, tools, prompts, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": skill_id, "name": name, "version": version}


@router.get("/skills")
async def list_skills(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, version, created_at FROM agent_skills WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, description, version, tools, prompts, created_at FROM agent_skills WHERE id = ? AND user_id = ?",
            (skill_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")
        result = dict(row)
        result["tools"] = json.loads(result.get("tools", "[]"))
        result["prompts"] = json.loads(result.get("prompts", "{}"))
        return result


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM agent_skills WHERE id = ? AND user_id = ?", (skill_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Skill not found")
    return {"ok": True}
