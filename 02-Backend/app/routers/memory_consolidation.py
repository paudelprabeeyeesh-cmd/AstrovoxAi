"""Memory consolidation routes (W1.3).

The consolidation service in ``app/memory/memory_consolidation.py`` had no
HTTP surface, so the router loader reported a missing module while the
feature was unreachable. This router wraps the real API.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.memory.memory_consolidation import MemoryConsolidationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory/consolidation", tags=["memory"])


@router.get("/stats")
async def consolidation_stats(
    authorization: Optional[str] = None,
) -> Dict[str, Any]:
    """Consolidation statistics for the calling user."""
    user_id = get_current_user(authorization)
    try:
        service = MemoryConsolidationService()
        stats = service.get_user_stats(user_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - log the reason, not a traceback
        logger.error(
            "consolidation.stats_failed user_id=%s reason=%s",
            user_id, str(exc)[:200],
        )
        raise HTTPException(
            status_code=500, detail="Consolidation stats unavailable"
        ) from exc
    return {"status": "OK", "user_id": user_id, "stats": stats}


class ConsolidationRunResponse(BaseModel):
    status: str
    user_id: str
    loaded: int = 0
    consolidated_count: int = 0
    pruned_count: int = 0


@router.post("/run", response_model=ConsolidationRunResponse)
async def run_consolidation(
    authorization: Optional[str] = None,
    dry_run: bool = False,
) -> ConsolidationRunResponse:
    """Run consolidation for the calling user's memories.

    ``dry_run`` loads and consolidates but skips the write-back, so an
    operator can preview the effect before it mutates the memory store.
    """
    user_id = get_current_user(authorization)
    try:
        service = MemoryConsolidationService()
        if dry_run:
            fragments = service.load_user_memories(user_id)
            service._consolidator.add_memories(fragments)
            result = service._consolidator.consolidate_all()
            return ConsolidationRunResponse(
                status="OK (dry run)",
                user_id=user_id,
                loaded=len(fragments),
                consolidated_count=result.get("consolidated_count", 0),
                pruned_count=result.get("pruned_count", 0),
            )
        result = service.consolidate_user(user_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "consolidation.run_failed user_id=%s dry_run=%s reason=%s",
            user_id, dry_run, str(exc)[:200],
        )
        raise HTTPException(
            status_code=500, detail="Consolidation failed"
        ) from exc
    return ConsolidationRunResponse(
        status="OK",
        user_id=user_id,
        loaded=result.get("loaded", 0),
        consolidated_count=result.get("consolidated_count", 0),
        pruned_count=result.get("pruned_count", 0),
    )
