import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["artifacts"])


@router.post("/artifacts")
async def create_artifact(title: str, content: str, artifact_type: str = "html", user_id: str = Depends(require_verified_email)):
    try:
        artifact_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO artifacts (id, user_id, title, content, artifact_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (artifact_id, user_id, title[:200], content[:100000], artifact_type, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": artifact_id, "title": title, "type": artifact_type, "url": f"/artifacts/{artifact_id}"}
    except Exception as e:
        logger.error(f"Artifact creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts")
async def list_artifacts(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, artifact_type, created_at FROM artifacts WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, content, artifact_type, created_at FROM artifacts WHERE id = ? AND user_id = ?",
            (artifact_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return dict(row)


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM artifacts WHERE id = ? AND user_id = ?", (artifact_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Artifact not found")
    return {"ok": True}
