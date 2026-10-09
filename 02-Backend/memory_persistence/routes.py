"""
Memory Consolidation API routes.

Endpoints:
- POST /memory/consolidation/run - Run consolidation for a user
- GET /memory/consolidation/stats/{user_id} - Get consolidation stats
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Form, status
from pydantic import BaseModel, Field

from memory_persistence.memory_consolidation import MemoryConsolidator, MemoryFragment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory/consolidation", tags=["memory-consolidation"])

_consolidators: Dict[str, MemoryConsolidator] = {}


def _get_consolidator(user_id: str) -> MemoryConsolidator:
    if user_id not in _consolidators:
        _consolidators[user_id] = MemoryConsolidator()
    return _consolidators[user_id]


class ConsolidationResponse(BaseModel):
    status: str
    duplicates_merged: int
    episodic_consolidated: int
    strengthened: int
    stale_pruned: int
    total_actions: int
    active_memories: int


class StatsResponse(BaseModel):
    total_memories: int
    active_memories: int
    avg_importance: float
    avg_access_count: float
    by_category: Dict[str, int]


class AddMemoryRequest(BaseModel):
    user_id: str = Field(..., max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)
    memory_id: str = Field(..., max_length=100)
    category: str = Field(default="general", max_length=50)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AddMemoryResponse(BaseModel):
    memory_id: str
    status: str


@router.post("/memory", response_model=AddMemoryResponse)
async def add_memory(request: AddMemoryRequest):
    consolidator = _get_consolidator(request.user_id)
    fragment = MemoryFragment(
        memory_id=request.memory_id,
        content=request.content,
        category=request.category,
        importance=request.importance,
        metadata=request.metadata,
    )
    consolidator.add_memory(fragment)
    return AddMemoryResponse(memory_id=request.memory_id, status="added")


@router.post("/run", response_model=ConsolidationResponse)
async def run_consolidation(user_id: str = Form(...)):
    consolidator = _get_consolidator(user_id)
    try:
        result = consolidator.consolidate_all()
        return ConsolidationResponse(
            status="completed",
            duplicates_merged=result["duplicates_merged"],
            episodic_consolidated=result["episodic_consolidated"],
            strengthened=result["strengthened"],
            stale_pruned=result["stale_pruned"],
            total_actions=result["total_actions"],
            active_memories=result["active_memories"],
        )
    except Exception as exc:
        logger.error("Consolidation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Consolidation failed") from exc


@router.get("/stats/{user_id}", response_model=StatsResponse)
async def get_stats(user_id: str):
    consolidator = _get_consolidator(user_id)
    stats = consolidator.get_stats()
    return StatsResponse(
        total_memories=stats.get("total_memories", 0),
        active_memories=stats.get("active_memories", 0),
        avg_importance=stats.get("avg_importance", 0.0),
        avg_access_count=stats.get("avg_access_count", 0.0),
        by_category=stats.get("by_category", {}),
    )
