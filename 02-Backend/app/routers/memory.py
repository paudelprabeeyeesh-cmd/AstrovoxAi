import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ...schemas import MemoryCreate, MemoryUpdate, MemoryOut, MemoryClassifyRequest, MemoryClassifyResponse
from ..memory_service import memory_service
from ..auth import require_verified_email, get_current_user
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory"])


@router.post("/memory", response_model=MemoryOut)
async def create_memory_endpoint(
    data: MemoryCreate, user_id: str = Depends(require_verified_email)
):
    result = memory_service.store_memory(user_id, data.key, data.value)
    return MemoryOut(
        id=result["id"],
        key=result["key"],
        value=result["value"],
        created_at=datetime.now(timezone.utc),
        memory_type=result.get("memory_type"),
        importance_score=result.get("importance_score", 0.5),
    )


@router.get("/memory", response_model=list[MemoryOut])
async def list_memories_endpoint(user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
            (user_id,),
        ).fetchall()
        return [
            MemoryOut(
                id=r["id"],
                key=r["key"],
                value=r["value"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


@router.get("/memory/search", response_model=list[MemoryOut])
async def search_memories_endpoint(user_id: str = Depends(get_current_user), q: str = ""):
    if not q:
        return []
    results = memory_service.search_memories(user_id, q, limit=5)
    return [
        MemoryOut(
            id=r["id"],
            key=r.get("key", ""),
            value=r["value"],
            created_at=r["created_at"],
            memory_type=r.get("memory_type"),
            importance_score=r.get("importance_score", 0.5),
        )
        for r in results
    ]


@router.put("/memory/{memory_id}", response_model=MemoryOut)
async def update_memory_endpoint(
    memory_id: str, data: MemoryUpdate, user_id: str = Depends(require_verified_email)
):
    with get_db() as conn:
        row = conn.execute(
            "UPDATE memories SET value = ? WHERE id = ? AND user_id = ?",
            (data.value, memory_id, user_id),
        )
        conn.commit()
        if row.rowcount == 0:
            raise HTTPException(status_code=404, detail="Memory not found")
        r = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        return MemoryOut(
            id=r["id"],
            key=r["key"],
            value=r["value"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )


@router.delete("/memory/{memory_id}")
async def delete_memory_endpoint(memory_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id)
        )
        conn.commit()
        if row.rowcount == 0:
            raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


@router.get("/memory/export")
async def export_memories_endpoint(user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {
            "user_id": user_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "memories": [dict(r) for r in rows],
        }


@router.post("/memory/classify", response_model=MemoryClassifyResponse)
async def classify_memory_endpoint(data: MemoryClassifyRequest, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM memories WHERE id = ? AND user_id = ?",
            (data.memory_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Memory not found")
        value = row["value"]
    memory_type, score = memory_service.classify_memory(value)
    return MemoryClassifyResponse(memory_id=data.memory_id, category=memory_type.value, confidence=score)
