"""
Extended Memory API routes.

Endpoints:
- POST /memory/long-term - Store long-term memory
- GET /memory/long-term - List long-term memories
- GET /memory/long-term/{memory_id} - Get long-term memory
- PUT /memory/long-term/{memory_id} - Update long-term memory
- DELETE /memory/long-term/{memory_id} - Delete long-term memory
- POST /memory/compress - Compress memories
- POST /memory/sync - Sync memories across layers
- GET /memory/timeline - Memory timeline
- GET /memory/profile/{user_id} - User memory profile
- GET /memory/visualization/timeline - Memory timeline for visualization
- GET /memory/visualization/distribution - Memory layer distribution
- GET /memory/visualization/heatmap - Memory activity heatmap
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..auth import require_verified_email, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory-extended"])

memory_manager = MemoryManager()


class LongTermMemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    category: str = Field("general", max_length=100)
    importance: float = Field(0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryCompressRequest(BaseModel):
    memories: list[dict[str, Any]] = Field(default_factory=list)
    max_length: int | None = None


class MemorySyncRequest(BaseModel):
    layers: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class MemoryVisualizationDistributionRequest(BaseModel):
    counts: dict[str, int] = Field(default_factory=dict)


class MemoryHeatmapRequest(BaseModel):
    memories: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/long-term")
async def store_long_term_memory(request: LongTermMemoryCreateRequest, user_id: str = Depends(require_verified_email)):
    try:
        memory_id = memory_manager.store_long_term(
            user_id=user_id,
            content=request.content,
            category=request.category,
            importance=request.importance,
            metadata=request.metadata,
        )
        memory_manager.record_memory_event("store_long_term", "long_term", {"memory_id": memory_id})
        return {"memory_id": memory_id, "status": "stored"}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/long-term")
async def list_long_term_memories(user_id: str = Depends(get_current_user), category: str | None = None, limit: int = 100):
    try:
        memories = memory_manager.list_long_term(user_id=user_id, category=category, limit=limit)
        return {"memories": memories}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/long-term/{memory_id}")
async def get_long_term_memory(memory_id: str, user_id: str = Depends(get_current_user)):
    try:
        mem = memory_manager.get_long_term(memory_id)
        if not mem:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return mem
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.put("/long-term/{memory_id}")
async def update_long_term_memory(memory_id: str, request: LongTermMemoryCreateRequest, user_id: str = Depends(require_verified_email)):
    try:
        updated = memory_manager.long_term_memory.update_memory(
            memory_id=memory_id,
            content=request.content,
            importance=request.importance,
            metadata=request.metadata,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        memory_manager.record_memory_event("update_long_term", "long_term", {"memory_id": memory_id})
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.delete("/long-term/{memory_id}")
async def delete_long_term_memory(memory_id: str, user_id: str = Depends(require_verified_email)):
    try:
        deleted = memory_manager.long_term_memory.delete_memory(memory_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        memory_manager.record_memory_event("delete_long_term", "long_term", {"memory_id": memory_id})
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/compress")
async def compress_memories(request: MemoryCompressRequest, user_id: str = Depends(require_verified_email)):
    try:
        compressed = memory_manager.compress_memories(request.memories)
        original_total = sum(len(m.get("content", "")) for m in request.memories)
        compressed_total = sum(len(c.get("content", "")) for c in compressed)
        return {
            "compressed": compressed,
            "original_total_length": original_total,
            "compressed_total_length": compressed_total,
        }
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/sync")
async def sync_memories(request: MemorySyncRequest, user_id: str = Depends(require_verified_email)):
    try:
        results = memory_manager.sync_memories(request.layers)
        return {"results": results}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/timeline")
async def memory_timeline(user_id: str = Depends(get_current_user), start: str | None = None, end: str | None = None):
    try:
        events = memory_manager.get_memory_timeline(user_id=user_id, start=start, end=end)
        return {"events": events}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/profile/{user_id}")
async def get_user_memory_profile(user_id: str):
    try:
        profile = memory_manager.get_user_profile(user_id=user_id)
        return profile
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/visualization/timeline")
async def memory_visualization_timeline(user_id: str = Depends(get_current_user), start: str | None = None, end: str | None = None):
    try:
        events = memory_manager.visualization.timeline(user_id=user_id, start=start, end=end)
        return {"events": events, "total": len(events)}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/visualization/distribution")
async def memory_visualization_distribution(user_id: str = Depends(get_current_user)):
    try:
        summary = memory_manager.get_memory_summary(int(user_id))
        counts = {
            "context": summary.get("context", {}).get("total_items", 0),
            "conversations": summary.get("conversations", {}).get("total", 0),
            "semantic": summary.get("semantic", {}).get("total_facts", 0),
            "episodic": summary.get("episodic", {}).get("total_events", 0),
            "procedural": summary.get("procedural", {}).get("total_procedures", 0),
            "workspaces": summary.get("workspaces", {}).get("total", 0),
        }
        distribution = memory_manager.visualization.layer_distribution(counts)
        return distribution
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/visualization/heatmap")
async def memory_visualization_heatmap(request: MemoryHeatmapRequest, user_id: str = Depends(require_verified_email)):
    try:
        data = memory_manager.visualization.memory_heatmap(request.memories)
        return {"data": data}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None
