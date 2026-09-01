"""Memory Engine API endpoints."""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from .auth_utils import get_user_id_from_token
from .memory_engine.engine import MemoryEngine

router = APIRouter(prefix="/api/memory-v2", tags=["memory-engine"])


class RememberRequest(BaseModel):
    content: str
    importance: Optional[int] = 1
    category: Optional[str] = "personal"


class RecallRequest(BaseModel):
    query: str
    category: Optional[str] = "personal"
    top_k: Optional[int] = 5


class ContextRequest(BaseModel):
    query: str
    max_tokens: Optional[int] = 1000
    category: Optional[str] = "personal"


@router.post("/remember")
async def remember(request: RememberRequest, authorization: str = Header(None)):
    """Store a new memory with semantic embedding."""
    user_id = get_user_id_from_token(authorization)

    engine = MemoryEngine(user_id)
    entry = await engine.remember(
        content=request.content,
        importance=request.importance or 1,
        category=request.category or "personal",
    )

    return {
        "status": "OK",
        "memory": {
            "id": entry.id,
            "content": entry.content,
            "importance": entry.importance,
            "category": entry.category,
            "has_embedding": entry.embedding is not None,
        },
    }


@router.post("/recall")
async def recall(request: RecallRequest, authorization: str = Header(None)):
    """Semantically search memories."""
    user_id = get_user_id_from_token(authorization)

    engine = MemoryEngine(user_id)
    results = await engine.recall(
        query=request.query,
        category=request.category or "personal",
        top_k=request.top_k or 5,
    )

    return {
        "status": "OK",
        "results": results,
        "count": len(results),
    }


@router.post("/context")
async def get_context(request: ContextRequest, authorization: str = Header(None)):
    """Get relevant context for injection into AI prompts."""
    user_id = get_user_id_from_token(authorization)

    engine = MemoryEngine(user_id)
    context = await engine.get_context(
        query=request.query,
        max_tokens=request.max_tokens or 1000,
        category=request.category or "personal",
    )

    return {
        "status": "OK",
        "context": context,
        "has_context": bool(context),
    }


@router.get("/analytics")
async def get_analytics(authorization: str = Header(None)):
    """Get memory analytics."""
    user_id = get_user_id_from_token(authorization)

    engine = MemoryEngine(user_id)
    return {
        "status": "OK",
        "analytics": {
            "personal": engine.get_analytics("personal"),
            "workspace": engine.get_analytics("workspace"),
            "conversation": engine.get_analytics("conversation"),
        },
    }
