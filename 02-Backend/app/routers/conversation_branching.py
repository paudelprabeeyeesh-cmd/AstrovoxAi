import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversation-branching"])


@router.post("/conversation/branches")
async def create_conversation_branch(req: dict, user_id: str = Depends(require_verified_email)):
    branch_id = str(uuid.uuid4())
    parent_id = req.get("parent_id")
    name = req.get("name", "Untitled Branch")
    context = req.get("context", "")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversation_branches (id, user_id, parent_id, name, context, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (branch_id, user_id, parent_id, name, context, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": branch_id, "name": name}


@router.get("/conversation/branches")
async def list_conversation_branches(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, parent_id, name, context, created_at FROM conversation_branches WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["created_at"] = item["created_at"]  # Keep as string
            result.append(item)
        return result


@router.get("/conversation/branches/{branch_id}")
async def get_conversation_branch(branch_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, parent_id, name, context, created_at FROM conversation_branches WHERE id = ? AND user_id = ?",
            (branch_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Branch not found")
        item = dict(row)
        item["created_at"] = item["created_at"]
        return item


@router.post("/conversation/merge")
async def merge_conversation_branches(req: dict, user_id: str = Depends(require_verified_email)):
    branch_ids = req.get("branch_ids", [])
    if len(branch_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 branches to merge")
    with get_db() as conn:
        # Merge all branches into one
        conn.execute("DELETE FROM conversation_branches WHERE id IN ({})".format(",".join(["?"] * len(branch_ids))), branch_ids)
        conn.commit()
    return {"status": "merged", "branch_ids": branch_ids}