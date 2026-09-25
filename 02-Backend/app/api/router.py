"""Temporal API router."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/temporal", tags=["temporal"])


class SnapshotCreateRequest(BaseModel):
    aggregate_id: str
    aggregate_type: str
    version: int
    state: Dict[str, Any]
    event_position: int
    metadata: Optional[Dict[str, Any]] = None


class TimeTravelRequest(BaseModel):
    aggregate_id: str
    timestamp: Optional[str] = None
    version: Optional[int] = None
    event_position: Optional[int] = None
    mode: str = "hybrid"


class RollbackRequest(BaseModel):
    aggregate_id: str
    target_version: int


class BranchCreateRequest(BaseModel):
    name: str
    branch_type: str
    parent_snapshot_id: str
    parent_version: int
    parent_branch_id: Optional[str] = None


class CausalChainRequest(BaseModel):
    chain_id: str
    chain_name: str
    event_ids: List[str]


@router.get("/health")
async def temporal_health() -> Dict[str, Any]:
    return {"status": "ok", "module": "temporal"}


@router.post("/snapshots")
async def create_snapshot(request: SnapshotCreateRequest) -> Dict[str, Any]:
    try:
        from ..temporal.snapshots import SnapshotEngine
        engine = SnapshotEngine()
        snapshot = engine.create_snapshot(
            aggregate_id=request.aggregate_id,
            aggregate_type=request.aggregate_type,
            version=request.version,
            state=request.state,
            event_position=request.event_position,
            metadata=request.metadata,
        )
        return {"snapshot_id": snapshot.snapshot_id, "version": snapshot.version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{aggregate_id}")
async def get_snapshots(aggregate_id: str) -> Dict[str, Any]:
    try:
        from ..temporal.snapshots import SnapshotEngine
        engine = SnapshotEngine()
        snapshots = engine.get_snapshots(aggregate_id)
        return {"aggregate_id": aggregate_id, "snapshots": [{"snapshot_id": s.snapshot_id, "version": s.version} for s in snapshots]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/time-travel")
async def time_travel(request: TimeTravelRequest) -> Dict[str, Any]:
    try:
        from ..temporal.time_travel_api import TimeTravelAPI, QueryMode, PointInTimeQuery
        api = TimeTravelAPI(None, None)
        query = PointInTimeQuery(
            query_id="",
            aggregate_id=request.aggregate_id,
            timestamp=None if not request.timestamp else __import__("datetime").datetime.fromisoformat(request.timestamp),
            version=request.version,
            event_position=request.event_position,
            mode=QueryMode(request.mode),
        )
        result = await api.query(query)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback(request: RollbackRequest) -> Dict[str, Any]:
    try:
        from ..temporal.rollback import TemporalRollbackAutomation
        automation = TemporalRollbackAutomation(None, None, None)
        result = automation.rollback_to_version(request.aggregate_id, request.target_version)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/branches")
async def create_branch(request: BranchCreateRequest) -> Dict[str, Any]:
    try:
        from ..temporal.branching import BranchTimelineManager, BranchType
        manager = BranchTimelineManager()
        branch = manager.create_branch(
            name=request.name,
            branch_type=BranchType(request.branch_type),
            parent_snapshot_id=request.parent_snapshot_id,
            parent_version=request.parent_version,
            parent_branch_id=request.parent_branch_id,
        )
        return {"branch_id": branch.branch_id, "name": branch.name, "status": branch.status.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branches/{branch_id}")
async def get_branch(branch_id: str) -> Dict[str, Any]:
    try:
        from ..temporal.branching import BranchTimelineManager
        manager = BranchTimelineManager()
        branch = manager.get_branch(branch_id)
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")
        return {"branch_id": branch.branch_id, "name": branch.name, "status": branch.status.value}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/causal/chains")
async def create_causal_chain(request: CausalChainRequest) -> Dict[str, Any]:
    try:
        from ..temporal.causal import CausalChainAnalyzer, CausalEvent, CausalEdge
        analyzer = CausalChainAnalyzer()
        events = [CausalEvent(event_id=eid, event_type="", aggregate_id="", version=0, occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)) for eid in request.event_ids]
        analyzer.add_events(events)
        chain = analyzer.build_chain(request.chain_id, request.chain_name, request.event_ids)
        return chain.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/causal/graph/{aggregate_id}")
async def get_causal_graph(aggregate_id: str) -> Dict[str, Any]:
    try:
        from ..temporal.causal import CausalChainAnalyzer
        analyzer = CausalChainAnalyzer()
        graph = analyzer.to_graph()
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def temporal_stats() -> Dict[str, Any]:
    try:
        from ..temporal.snapshots import SnapshotEngine
        from ..temporal.causal import CausalChainAnalyzer
        from ..temporal.diffing import StateDiffer
        return {
            "snapshots": SnapshotEngine().get_stats(),
            "causal": CausalChainAnalyzer().get_stats(),
            "diffing": "ok",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
