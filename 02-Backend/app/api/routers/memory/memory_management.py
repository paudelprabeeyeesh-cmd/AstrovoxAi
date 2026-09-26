import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory-management"])


@router.post("/memory/store")
async def store_memory(req: dict, user_id: str = Depends(require_verified_email)):
    memory_id = str(uuid.uuid4())
    content = req.get("content", "")
    memory_type = req.get("memory_type", "fact")
    importance = req.get("importance", 0.5)
    incognito = req.get("incognito", False)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO memories (id, user_id, key, value, memory_type, importance_score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (memory_id, user_id, f"key_{memory_id}", content, memory_type, importance, datetime.now(timezone.utc).isoformat()),
        )
        if incognito:
            conn.execute(
                "INSERT INTO memory_incognito (memory_id, user_id, created_at) VALUES (?, ?, ?)",
                (memory_id, user_id, datetime.now(timezone.utc).isoformat()),
            )
        conn.commit()
    return {"id": memory_id, "incognito": incognito}


@router.get("/memory/search")
async def search_memory(query: str, incognito_only: bool = False, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        if incognito_only:
            rows = conn.execute(
                "SELECT m.id, m.key, m.value, m.memory_type, m.importance_score, m.created_at FROM memories m "
                "JOIN memory_incognito mi ON mi.memory_id = m.id WHERE m.user_id = ? AND m.value LIKE ? ORDER BY m.created_at DESC",
                (user_id, f"%{query}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, key, value, memory_type, importance_score, created_at FROM memories WHERE user_id = ? AND value LIKE ? ORDER BY importance_score DESC, created_at DESC",
                (user_id, f"%{query}%"),
            ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["content"] = item.pop("value")
            item["key"] = item.pop("key")
            result.append(item)
        return result


@router.get("/memory/incognito/list")
async def list_incognito_memories(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT m.id, m.content, m.created_at, mi.expires_at FROM memories m "
            "JOIN memory_incognito mi ON mi.memory_id = m.id WHERE mi.user_id = ? ORDER BY m.created_at DESC",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            items = dict(item)
            items["content"] = r["content"]
            result.append(items)
        return result


@router.post("/memory/incognito/{memory_id}/revoke")
async def revoke_incognito_memory(memory_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT mi.memory_id FROM memory_incognito mi WHERE mi.memory_id = ? AND mi.user_id = ?",
            (memory_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incognito memory not found")
        conn.execute("DELETE FROM memory_incognito WHERE memory_id = ?", (memory_id,))
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
    return {"revoked": True, "memory_id": memory_id}


@router.post("/memory/classify")
async def classify_memory_importance(req: dict, user_id: str = Depends(require_verified_email)):
    content = req.get("content", "")
    import random
    importance = round(random.uniform(0.1, 0.9), 2)
    memory_type = "fact" if importance < 0.5 else "preference"
    return {
        "content": content[:100],
        "importance": importance,
        "memory_type": memory_type,
        "classification": "low" if importance < 0.3 else ("medium" if importance < 0.7 else "high"),
    }
