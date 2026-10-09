"""
LLM Governance API.

Exposes unified endpoints for:
- Multi-model routing
- Reasoning traces
- Context compression
- Self-correction loop
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.llm_governance import (
    LLMGovernanceService, ReasoningPolicy, RouteRequest, CompressRequest, CorrectRequest
)
from ..auth_utils import get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-governance", tags=["llm-governance"])

_service = LLMGovernanceService()


class RouteBody(BaseModel):
    user_id: Optional[int] = Field(None)
    task_type: Optional[str] = Field(None)
    capabilities: List[str] = Field(default_factory=list)
    optimize_for: str = Field("balanced")
    policy: str = Field("balanced")
    fallback_strategy: str = Field("cross_provider")
    max_tokens: Optional[int] = Field(None)
    requires_vision: bool = Field(False)
    requires_function_calling: bool = Field(True)
    preferred_model: Optional[str] = Field(None)
    request_id: Optional[str] = Field(None)


class CompressBody(BaseModel):
    context: str = Field(..., min_length=1, max_length=200000)
    max_tokens: int = Field(..., gt=0, le=128000)
    query: Optional[str] = Field(None, max_length=20000)
    strategy: str = Field("hybrid")


class CorrectBody(BaseModel):
    response: str = Field(..., min_length=1, max_length=100000)
    context: Optional[str] = Field(None, max_length=200000)
    request_id: Optional[str] = Field(None)


class ProcessBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=100000)
    user_id: Optional[int] = Field(None)
    task_type: Optional[str] = Field(None)
    context: Optional[str] = Field(None, max_length=200000)
    reasoning_policy: str = Field("balanced")
    request_id: Optional[str] = Field(None)


class TraceSummaryResponse(BaseModel):
    request_id: str
    user_id: int
    user_message: str
    start_time: str
    end_time: Optional[str]
    duration_ms: Optional[int]
    final_response: Optional[str]
    events: List[Dict[str, Any]]
    reasoning_chain: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    summary: Dict[str, Any]


@router.post("/route")
async def route_model(body: RouteBody):
    from app.model_router_v2 import RoutingPolicy, FallbackStrategy

    policy_map = {
        "strict": RoutingPolicy.STRICT,
        "balanced": RoutingPolicy.BALANCED,
        "cost_first": RoutingPolicy.COST_FIRST,
        "cost": RoutingPolicy.COST_FIRST,
        "speed_first": RoutingPolicy.SPEED_FIRST,
        "speed": RoutingPolicy.SPEED_FIRST,
        "quality_first": RoutingPolicy.QUALITY_FIRST,
        "quality": RoutingPolicy.QUALITY_FIRST,
    }
    fallback_map = {
        "none": FallbackStrategy.NONE,
        "same_provider": FallbackStrategy.SAME_PROVIDER,
        "cross_provider": FallbackStrategy.CROSS_PROVIDER,
        "local_fallback": FallbackStrategy.LOCAL_FALLBACK,
    }
    policy = policy_map.get(body.policy.lower(), RoutingPolicy.BALANCED)
    fallback = fallback_map.get(body.fallback_strategy.lower(), FallbackStrategy.CROSS_PROVIDER)
    route_request = RouteRequest(
        user_id=body.user_id,
        task_type=body.task_type,
        capabilities=body.capabilities,
        optimize_for=body.optimize_for,
        policy=policy,
        fallback_strategy=fallback,
        max_tokens=body.max_tokens,
        requires_vision=body.requires_vision,
        requires_function_calling=body.requires_function_calling,
        preferred_model=body.preferred_model,
        request_id=body.request_id,
    )
    try:
        result = await _service.route(route_request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "OK", "result": result}


@router.post("/compress")
async def compress_context(body: CompressBody):
    strategy_map = {
        "extractive": "extractive",
        "abstractive": "abstractive",
        "hybrid": "hybrid",
        "token_truncation": "token_truncation",
    }
    strategy_key = strategy_map.get(body.strategy.lower(), "hybrid")
    request = CompressRequest(
        context=body.context,
        max_tokens=body.max_tokens,
        query=body.query,
        strategy=strategy_key,
    )
    try:
        result = await _service.compress(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "OK", "result": result}


@router.post("/correct")
async def correct_response(body: CorrectBody):
    request = CorrectRequest(
        response=body.response,
        context=body.context,
        request_id=body.request_id,
    )
    try:
        result = await _service.correct(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "OK", "result": result}


@router.post("/process")
async def process_intelligent_request(body: ProcessBody):
    policy_map = {
        "direct": "direct",
        "balanced": "balanced",
        "deep": "deep",
        "self_corrected": "self_corrected",
    }
    policy = policy_map.get(body.reasoning_policy.lower(), "balanced")
    try:
        result = await _service.process(
            user_message=body.message,
            user_id=body.user_id,
            task_type=body.task_type,
            context=body.context,
            reasoning_policy=policy,
            request_id=body.request_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "OK", "result": result}


@router.get("/trace/{request_id}", response_model=TraceSummaryResponse)
async def get_trace(request_id: str):
    trace = _service.tracer.get_trace(request_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    data = trace.to_dict()
    return TraceSummaryResponse(
        request_id=data["request_id"],
        user_id=data["user_id"],
        user_message=data["user_message"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        duration_ms=data["duration_ms"],
        final_response=data["final_response"],
        events=data["events"],
        reasoning_chain=data["reasoning_chain"],
        metadata=data["metadata"],
        summary=data["summary"],
    )


@router.get("/traces")
async def list_traces(user_id: Optional[int] = None, limit: int = 50):
    traces = []
    if user_id:
        traces = _service.tracer.get_user_traces(user_id, limit=limit)
    else:
        all_traces = list(_service.tracer.traces.values())
        all_traces.sort(key=lambda t: t.start_time, reverse=True)
        traces = [t.to_dict() for t in all_traces[:limit]]
    return {"status": "OK", "traces": traces, "count": len(traces)}


@router.get("/policies")
async def list_policies():
    return {
        "routing_policies": ["strict", "balanced", "cost_first", "speed_first", "quality_first"],
        "reasoning_policies": [policy.value for policy in ReasoningPolicy],
        "compression_strategies": [
            "extractive",
            "abstractive",
            "hybrid",
            "token_truncation",
        ],
    }
