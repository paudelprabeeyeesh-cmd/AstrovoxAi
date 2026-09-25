import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["research"])


@router.post("/research/deep")
async def deep_research_endpoint(query: str, depth: str = "medium", user_id: str = Depends(require_verified_email)):
    try:
        research_id = str(uuid.uuid4())
        steps = {"quick": 3, "medium": 7, "deep": 15}.get(depth, 7)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO research_reports (id, user_id, query, depth, steps, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (research_id, user_id, query[:1000], depth, steps, "running", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {
            "id": research_id,
            "query": query[:200],
            "depth": depth,
            "steps": steps,
            "status": "running",
        }
    except Exception as e:
        logger.error(f"Deep research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/{research_id}")
async def get_research_report(research_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, query, depth, steps, status, result, created_at FROM research_reports WHERE id = ? AND user_id = ?",
            (research_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Research report not found")
        return dict(row)
