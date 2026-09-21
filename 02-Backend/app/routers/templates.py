import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["templates"])


@router.post("/templates")
async def create_template(req: dict, user_id: str = Depends(require_verified_email)):
    template_id = str(uuid.uuid4())
    name = req.get("name", "Untitled Template")
    content = req.get("content", "")
    description = req.get("description", "")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO templates (id, user_id, name, description, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (template_id, user_id, name, description, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": template_id, "name": name}


@router.get("/templates")
async def list_templates(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, created_at FROM templates WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/templates/{template_id}")
async def get_template(template_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, description, content, created_at FROM templates WHERE id = ? AND user_id = ?",
            (template_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        item = dict(row)
        item["created_at"] = item["created_at"]
        return item


@router.post("/templates/{template_id}/use")
async def use_template(template_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT content FROM templates WHERE id = ? AND user_id = ?",
            (template_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        content = row["content"]
    return {"content": content}