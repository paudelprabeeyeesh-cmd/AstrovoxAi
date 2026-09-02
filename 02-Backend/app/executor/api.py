"""FastAPI router exposing the AI Execution Engine (Stage 34)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth_utils import get_current_user

from .cluster import Worker, get_worker_registry, seed_default_workers
from .compiler import Compiler, ExecutionGraph, Step, compile_program
from .dsl import parse
from .learning import get_learning_engine
from .memory_brain import MemoryType, get_memory_brain
from .performance import get_cache, get_profiler
from .reasoning import ReasoningStrategy, get_reasoning_engine
from .reliability import FaultType, get_chaos_suite
from .runtime import execute_plan, get_runtime

router = APIRouter(prefix="/executor", tags=["executor"])


# ---- Compilation ----------------------------------------------------------


class CompileRequest(BaseModel):
    source: str


@router.post("/compile")
async def compile_source(req: CompileRequest, user=Depends(get_current_user)) -> Dict[str, Any]:
    try:
        program = parse(req.source)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"parse error: {exc}")
    graph = compile_program(program)
    return graph.to_dict()


# ---- Execution -----------------------------------------------------------


class ExecuteRequest(BaseModel):
    source: str
    cache: bool = True


@router.post("/execute")
async def execute_source(req: ExecuteRequest, user=Depends(get_current_user)) -> Dict[str, Any]:
    try:
        program = parse(req.source)
        graph = compile_program(program)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"compile error: {exc}")
    if req.cache:
        cached = get_cache().get(graph.cache_key)
        if cached is not None:
            return {"cache_hit": True, "graph": cached}
    result = await execute_plan(graph)
    get_cache().set(graph.cache_key, result)
    return result


# ---- Memory Brain --------------------------------------------------------


class MemoryRememberRequest(BaseModel):
    content: Any
    type: str = "long_term"
    importance: float = 1.0
    confidence: float = 1.0
    tags: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


@router.post("/memory/remember")
async def memory_remember(req: MemoryRememberRequest) -> Dict[str, Any]:
    item = get_memory_brain().remember(
        req.content,
        type=MemoryType(req.type),
        importance=req.importance,
        confidence=req.confidence,
        tags=req.tags,
        session_id=req.session_id,
    )
    return item.to_dict()


class MemoryRecallRequest(BaseModel):
    query: str
    type: Optional[str] = None
    limit: int = 10


@router.post("/memory/recall")
async def memory_recall(req: MemoryRecallRequest) -> Dict[str, Any]:
    mtype = MemoryType(req.type) if req.type else None
    items = get_memory_brain().recall(req.query, type=mtype, limit=req.limit)
    return {"count": len(items), "items": [i.to_dict() for i in items]}


@router.get("/memory/stats")
async def memory_stats() -> Dict[str, Any]:
    return get_memory_brain().stats()


# ---- Reasoning -----------------------------------------------------------


class ReasoningRequest(BaseModel):
    problem: str
    strategies: Optional[List[str]] = None
    fact_limit: int = 5


@router.post("/reason")
async def reason(req: ReasoningRequest) -> Dict[str, Any]:
    strategies = [ReasoningStrategy(s) for s in (req.strategies or [])]
    result = get_reasoning_engine().solve(
        req.problem,
        strategies=strategies or None,
        fact_limit=req.fact_limit,
    )
    return result.to_dict()


# ---- Learning ------------------------------------------------------------


class FeedbackRequest(BaseModel):
    category: str
    rating: float
    comment: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/learning/feedback")
async def learning_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    engine = get_learning_engine()
    event = engine.record_feedback(
        req.category,
        req.rating,
        comment=req.comment,
        **req.metadata,
    )
    return event.to_dict()


@router.get("/learning/report")
async def learning_report() -> Dict[str, Any]:
    return get_learning_engine().improvement_report()


@router.get("/learning/summary")
async def learning_summary() -> Dict[str, Any]:
    return get_learning_engine().summary()


# ---- Performance ---------------------------------------------------------


@router.get("/performance/profiler")
async def profiler_summary() -> Dict[str, Any]:
    return get_profiler().summary()


@router.get("/performance/cache")
async def cache_stats() -> Dict[str, Any]:
    return get_cache().stats()


# ---- Chaos / Reliability -------------------------------------------------


class ChaosExperimentRequest(BaseModel):
    name: str
    target: str
    fault: str
    probability: float = 1.0
    latency_ms: float = 0.0


@router.post("/chaos/experiment")
async def chaos_experiment(req: ChaosExperimentRequest) -> Dict[str, Any]:
    suite = get_chaos_suite()
    result = await suite.experiment(
        req.name,
        req.target,
        FaultType(req.fault),
        probability=req.probability,
        latency_ms=req.latency_ms,
    )
    return result


@router.get("/chaos/results")
async def chaos_results() -> Dict[str, Any]:
    return {"results": get_chaos_suite().results()}


# ---- Cluster -------------------------------------------------------------


@router.get("/cluster/workers")
async def cluster_workers() -> Dict[str, Any]:
    seed_default_workers()
    registry = get_worker_registry()
    return {"workers": registry.list(), "status": registry.status()}