"""
Memory controls API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...services.memory.memory_manager import MemoryManager
from ...core.context_manager import ContextChunk, LongContextManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

memory_manager = MemoryManager()
context_manager = LongContextManager()


class MemoryCreateRequest(BaseModel):
    user_id: str = Field(..., max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)
    memory_type: str = Field("semantic", max_length=50)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemorySearchRequest(BaseModel):
    user_id: str = Field(..., max_length=100)
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(10, ge=1, le=100)


class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    metadata: Dict[str, Any]
    score: float


@router.post("/add")
async def add_memory(request: MemoryCreateRequest):
    try:
        if request.memory_type == "semantic":
            from ...services.memory.semantic_memory import FactCategory
            memory_manager.add_fact(
                fact_key=f"memory_{request.user_id}_{hash(request.content)}",
                fact_value=request.content,
                category=FactCategory.PREFERENCE,
                user_explicit=True,
            )
        elif request.memory_type == "episodic":
            from ...services.memory.episodic_memory import EventType
            memory_manager.add_event(
                user_id=int(request.user_id),
                event_type=EventType.LEARNING_EVENT,
                title="Memory",
                description=request.content,
                significance=0.5,
            )
        else:
            context_manager.add_memory(request.user_id, ContextChunk(text=request.content, token_count=len(request.content.split()), importance=0.5, metadata=request.metadata))
        return {"status": "OK", "memory_type": request.memory_type}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/search")
async def search_memory(request: MemorySearchRequest):
    try:
        import asyncio
        matches = asyncio.run(memory_manager.retrieve_relevant_memory(query=request.query, user_id=int(request.user_id), limit=request.limit))
        return {"status": "OK", "results": matches}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/summary/{user_id}")
async def get_memory_summary(user_id: str):
    try:
        summary = memory_manager.get_memory_summary(int(user_id))
        return {"status": "OK", "summary": summary}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
