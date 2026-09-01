"""Multi-Agent and Enhanced Memory API routes."""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from typing import Optional

from .multi_agent import collaboration_manager, TaskStatus
from .memory_enhanced import memory_store
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/agents", tags=["agents"])


class CreateSessionRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)


@router.post("/sessions")
async def create_session(request: CreateSessionRequest, authorization: str = Header(None)):
    """Create a multi-agent collaboration session."""
    user_id = get_user_id_from_token(authorization)
    session = collaboration_manager.create_session(user_id, request.goal)
    return {
        "status": "OK",
        "session": {
            "id": session.id,
            "goal": session.goal,
            "status": session.status.value,
            "tasks": [
                {
                    "id": t.id,
                    "role": t.role.value,
                    "description": t.description,
                    "status": t.status.value,
                }
                for t in session.tasks
            ],
        },
    }


@router.post("/sessions/{session_id}/run")
async def run_session(session_id: str, authorization: str = Header(None)):
    """Run a collaboration session."""
    user_id = get_user_id_from_token(authorization)
    try:
        session = await collaboration_manager.run_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "OK",
        "session": {
            "id": session.id,
            "goal": session.goal,
            "status": session.status.value,
            "result": session.result,
            "tasks": [
                {
                    "id": t.id,
                    "role": t.role.value,
                    "status": t.status.value,
                    "result": t.result,
                }
                for t in session.tasks
            ],
            "messages": [
                {
                    "from": m.from_agent,
                    "to": m.to_agent,
                    "content": m.content,
                    "type": m.message_type,
                }
                for m in session.messages
            ],
        },
    }


@router.get("/sessions")
async def list_sessions(authorization: str = Header(None)):
    """List user's collaboration sessions."""
    user_id = get_user_id_from_token(authorization)
    sessions = collaboration_manager.get_user_sessions(user_id)
    return {
        "status": "OK",
        "sessions": [
            {
                "id": s.id,
                "goal": s.goal,
                "status": s.status.value,
                "task_count": len(s.tasks),
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, authorization: str = Header(None)):
    """Get session details."""
    user_id = get_user_id_from_token(authorization)
    session = collaboration_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "OK",
        "session": {
            "id": session.id,
            "goal": session.goal,
            "status": session.status.value,
            "result": session.result,
        },
    }


# Enhanced Memory Routes

memory_router = APIRouter(prefix="/memory-v2", tags=["memory"])


class AddMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    memory_type: str = "general"
    importance: float = 1.0
    tags: list[str] = []


class AddEpisodicRequest(BaseModel):
    title: str
    summary: str
    participants: list[str] = []
    outcome: str = ""
    importance: float = 1.0


class AddSemanticRequest(BaseModel):
    fact: str
    category: str = "general"
    confidence: float = 1.0


@memory_router.post("/")
async def add_memory(request: AddMemoryRequest, authorization: str = Header(None)):
    """Add a long-term memory."""
    user_id = get_user_id_from_token(authorization)
    entry = memory_store.add_memory(
        user_id=user_id,
        content=request.content,
        memory_type=request.memory_type,
        importance=request.importance,
        tags=request.tags,
    )
    return {
        "status": "OK",
        "memory": {
            "id": entry.id,
            "content": entry.content,
            "type": entry.memory_type,
            "importance": entry.importance,
        },
    }


@memory_router.get("/search")
async def search_memories(
    authorization: str = Header(None),
    q: str = "",
    memory_type: str = None,
    limit: int = 10,
):
    """Search memories with ranking."""
    user_id = get_user_id_from_token(authorization)
    results = memory_store.search(user_id, query=q, memory_type=memory_type, limit=limit)
    return {
        "status": "OK",
        "memories": [
            {
                "id": m.id,
                "content": m.content,
                "type": m.memory_type,
                "importance": m.importance,
                "access_count": m.access_count,
            }
            for m in results
        ],
    }


@memory_router.post("/episodic")
async def add_episodic(request: AddEpisodicRequest, authorization: str = Header(None)):
    """Add an episodic memory."""
    user_id = get_user_id_from_token(authorization)
    memory = memory_store.add_episodic(
        user_id=user_id,
        title=request.title,
        summary=request.summary,
        participants=request.participants,
        outcome=request.outcome,
        importance=request.importance,
    )
    return {
        "status": "OK",
        "memory": {
            "id": memory.id,
            "title": memory.title,
            "summary": memory.summary,
        },
    }


@memory_router.get("/episodic")
async def get_episodic(authorization: str = Header(None), limit: int = 20):
    """Get episodic memories."""
    user_id = get_user_id_from_token(authorization)
    memories = memory_store.get_episodic(user_id, limit=limit)
    return {
        "status": "OK",
        "memories": [
            {
                "id": m.id,
                "title": m.title,
                "summary": m.summary,
                "timestamp": m.timestamp,
            }
            for m in memories
        ],
    }


@memory_router.post("/semantic")
async def add_semantic(request: AddSemanticRequest, authorization: str = Header(None)):
    """Add a semantic memory."""
    user_id = get_user_id_from_token(authorization)
    memory = memory_store.add_semantic(
        user_id=user_id,
        fact=request.fact,
        category=request.category,
        confidence=request.confidence,
    )
    return {
        "status": "OK",
        "memory": {
            "id": memory.id,
            "fact": memory.fact,
            "category": memory.category,
        },
    }


@memory_router.get("/semantic")
async def get_semantic(authorization: str = Header(None), category: str = None):
    """Get semantic memories."""
    user_id = get_user_id_from_token(authorization)
    memories = memory_store.get_semantic(user_id, category=category)
    return {
        "status": "OK",
        "memories": [
            {
                "id": m.id,
                "fact": m.fact,
                "category": m.category,
                "confidence": m.confidence,
            }
            for m in memories
        ],
    }


@memory_router.get("/stats")
async def get_memory_stats(authorization: str = Header(None)):
    """Get memory statistics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **memory_store.get_stats(user_id)}
