import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["templates"])


@router.post("/templates")
async def create_template(req: dict, user_id: str = Depends(require_verified_email)):
    template_id = str(uuid.uuid4())
    name = req.get("name", "Untitled Template")
    content = req.get("content", "")
    prompt = content
    description = req.get("description", "")
    with get_db() as conn:
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(templates)").fetchall()]
        cols = ["id", "user_id", "name", "prompt"]
        vals = [template_id, user_id, name, prompt]
        if "description" in existing_cols:
            cols.append("description")
            vals.append(description)
        if "content" in existing_cols:
            cols.append("content")
            vals.append(content)
        cols.append("created_at")
        vals.append(datetime.now(timezone.utc).isoformat())
        placeholders = ", ".join(["?"] * len(vals))
        conn.execute(
            f"INSERT INTO templates ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
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
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(templates)").fetchall()]
        select_col = "content" if "content" in existing_cols else "prompt"
        cols = ["id", "name", "description", select_col, "created_at"]
        row = conn.execute(
            f"SELECT {', '.join(cols)} FROM templates WHERE id = ? AND user_id = ?",
            (template_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        item = dict(row)
        if "content" not in item and "prompt" in item:
            item["content"] = item.pop("prompt")
        item["created_at"] = item["created_at"]
        return item


@router.post("/templates/{template_id}/use")
async def use_template(template_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(templates)").fetchall()]
        select_col = "content" if "content" in existing_cols else "prompt"
        row = conn.execute(
            f"SELECT {select_col} FROM templates WHERE id = ? AND user_id = ?",
            (template_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        col_name = "content" if "content" in existing_cols else "prompt"
        content = row[col_name]
    return {"content": content}