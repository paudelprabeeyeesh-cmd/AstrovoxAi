"""Memory API router."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .models import MemoryCreate, MemoryResponse, MemorySearch, MemorySummary
from .service import MemoryService

logger = logging.getLogger(__name__)
memory_service = MemoryService()
router = APIRouter(prefix="/memory", tags=["memory"])


class MessageResponse(BaseModel):
    message: str


@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(body: MemoryCreate, user_id: str = Depends(lambda: "user-1")):
    body.user_id = user_id
    return memory_service.create_memory(body)


@router.get("/search", response_model=list[tuple[MemoryResponse, float]])
async def search_memories(q: str, limit: int = 10, user_id: str = Depends(lambda: "user-1")):
    body = MemorySearch(query=q, limit=limit)
    return memory_service.search_memories(body)


@router.get("/summary", response_model=MemorySummary)
async def memory_summary(user_id: str = Depends(lambda: "user-1")):
    return memory_service.get_summary(user_id)


@router.delete("/{memory_id}", response_model=MessageResponse)
async def delete_memory(memory_id: str):
    if not memory_service.delete_memory(memory_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return MessageResponse(message="Memory deleted successfully")
