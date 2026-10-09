"""
AI Orchestration Router
=======================
Exposes multi-model routing, reasoning traces, context compression,
and self-correction loop as REST endpoints.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth_utils import get_user_id_from_token
from ..model_router_v2 import (
    MultiModelRouter,
    RoutingRequest,
    RoutingPolicy,
    FallbackStrategy,
    RoutingResult,
)
from ..context_compression import ContextCompressor, CompressionStrategy
from ..self_correction import SelfCorrectionLoop
from ..intelligence.execution_tracer import ExecutionTracer
from ..providers import ProviderFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-orchestration"])

_tracer = ExecutionTracer()
_compressor = ContextCompressor()
_self_correction = SelfCorrectionLoop()
_multi_model_router = MultiModelRouter()
_multi_model_router.set_tracer(_tracer)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class _ChatMessage(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=1, max_length=100000)


class RouteRequest(BaseModel):
    task_type: Optional[str] = Field(None, max_length=200)
    capabilities: List[str] = Field(default_factory=lambda: ["chat", "completion"])
    optimize_for: str = Field("balanced", max_length=50)
    policy: RoutingPolicy = Field(RoutingPolicy.BALANCED)
    fallback_strategy: FallbackStrategy = Field(FallbackStrategy.CROSS_PROVIDER)
    max_tokens: Optional[int] = Field(None, ge=1, le=32768)
    requires_vision: bool = False
    requires_function_calling: bool = True
    preferred_model: Optional[str] = Field(None, max_length=200)


class ChatWithFallbackRequest(BaseModel):
    messages: List[_ChatMessage]
    task_type: Optional[str] = Field(None, max_length=200)
    optimize_for: str = Field("balanced", max_length=50)
    policy: RoutingPolicy = Field(RoutingPolicy.BALANCED)
    fallback_strategy: FallbackStrategy = Field(FallbackStrategy.CROSS_PROVIDER)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2000, ge=1, le=32768)
    system_prompt: Optional[str] = Field(None, max_length=4000)


class CompressRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=200000)
    max_tokens: int = Field(4096, ge=1, le=32768)
    query: Optional[str] = Field(None, max_length=10000)
    strategy: CompressionStrategy = Field(CompressionStrategy.HYBRID)


class ExtractImportantRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=200000)
    query: str = Field(..., min_length=1, max_length=10000)


class SelfCorrectionRequest(BaseModel):
    response: str = Field(..., min_length=1, max_length=200000)
    context: Optional[str] = Field(None, max_length=200000)


class ReasoningStepRequest(BaseModel):
    step: str = Field(..., min_length=1, max_length=200)
    thought: str = Field(..., min_length=1, max_length=4000)
    evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Multi-model routing
# ---------------------------------------------------------------------------


@router.post("/routing/route")
async def route_request(
    request: RouteRequest,
    user_id: str = Depends(get_user_id_from_token),
):
    request_id = str(uuid.uuid4())
    tracer = ExecutionTracer()
    tracer.start_trace(
        request_id=request_id,
        user_id=int(user_id) if user_id.isdigit() else 0,
        user_message=f"route:{request.task_type or 'general'}",
    )

    req = RoutingRequest(
        user_id=int(user_id) if user_id.isdigit() else None,
        task_type=request.task_type,
        capabilities=request.capabilities,
        optimize_for=request.optimize_for,
        policy=request.policy,
        fallback_strategy=request.fallback_strategy,
        max_tokens=request.max_tokens,
        requires_vision=request.requires_vision,
        requires_function_calling=request.requires_function_calling,
        preferred_model=request.preferred_model,
        trace=tracer,
        request_id=request_id,
    )
    result = await _multi_model_router.route(req)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No suitable model available for routing",
        )
    tracer.end_trace(request_id, f"Selected model {result.model_id}")
    return {
        "request_id": request_id,
        "routing": {
            "model_id": result.model_id,
            "provider_name": result.provider_name,
            "reason": result.reason,
            "fallback_chain": result.fallback_chain,
            "estimated_cost_usd": result.estimated_cost_usd,
            "estimated_latency_ms": result.estimated_latency_ms,
            "confidence": result.confidence,
            "metadata": result.metadata,
        },
    }


@router.post("/routing/chat")
async def chat_with_fallback(
    request: ChatWithFallbackRequest,
    user_id: str = Depends(get_user_id_from_token),
):
    request_id = str(uuid.uuid4())
    tracer = ExecutionTracer()
    tracer.start_trace(
        request_id=request_id,
        user_id=int(user_id) if user_id.isdigit() else 0,
        user_message=request.messages[-1].content if request.messages else "",
    )

    req = RoutingRequest(
        user_id=int(user_id) if user_id.isdigit() else None,
        task_type=request.task_type,
        capabilities=["chat", "completion"],
        optimize_for=request.optimize_for,
        policy=request.policy,
        fallback_strategy=request.fallback_strategy,
        max_tokens=request.max_tokens,
        trace=tracer,
        request_id=request_id,
    )
    messages = [
        ProviderChatMessage(role=m.role, content=m.content)
        for m in request.messages
    ]
    try:
        response = await _multi_model_router.chat_with_fallback(
            request=req,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    tracer.end_trace(request_id, response.content)
    return {
        "request_id": request_id,
        "content": response.content,
        "model": response.model,
        "provider": response.provider,
        "tokens_used": response.tokens_used,
        "finish_reason": response.finish_reason,
        "metadata": response.metadata,
    }


@router.get("/routing/models")
async def list_routing_models():
    try:
        from ..providers.models import list_models
        models = list_models()
        return {
            "models": [
                {
                    "id": m.id,
                    "provider": m.provider,
                    "display_name": m.display_name,
                    "supports_streaming": m.supports_streaming,
                    "max_tokens": m.max_tokens,
                    "description": m.description,
                }
                for m in models
            ]
        }
    except Exception as exc:
        logger.error("Failed to list models: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list models",
        ) from exc


# ---------------------------------------------------------------------------
# Reasoning traces
# ---------------------------------------------------------------------------


@router.post("/traces")
async def start_trace(
    user_message: str,
    user_id: str = Depends(get_user_id_from_token),
):
    request_id = str(uuid.uuid4())
    _tracer.start_trace(
        request_id=request_id,
        user_id=int(user_id) if user_id.isdigit() else 0,
        user_message=user_message,
    )
    return {"request_id": request_id}


@router.get("/traces/{request_id}")
async def get_trace(request_id: str, user_id: str = Depends(get_user_id_from_token)):
    trace = _tracer.get_trace(request_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found",
        )
    return trace.to_dict()


@router.get("/traces/user/{user_id}")
async def get_user_traces(limit: int = 50):
    uid = int(user_id) if user_id.isdigit() else 0
    return {"traces": _tracer.get_user_traces(uid, limit=limit)}


@router.post("/traces/{request_id}/reasoning-step")
async def add_reasoning_step(
    request_id: str,
    step_request: ReasoningStepRequest,
    user_id: str = Depends(get_user_id_from_token),
):
    trace = _tracer.get_trace(request_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found",
        )
    _tracer.trace_reasoning_step(
        request_id=request_id,
        step=step_request.step,
        thought=step_request.thought,
        evidence=step_request.evidence,
        confidence=step_request.confidence,
        metadata=step_request.metadata,
    )
    return {"status": "ok"}


@router.post("/traces/{request_id}/complete")
async def complete_trace(
    request_id: str,
    final_response: str,
    user_id: str = Depends(get_user_id_from_token),
):
    trace = _tracer.get_trace(request_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found",
        )
    _tracer.end_trace(request_id, final_response)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Context compression
# ---------------------------------------------------------------------------


@router.post("/compression/compress")
async def compress_context(
    request: CompressRequest,
    user_id: str = Depends(get_user_id_from_token),
):
    request_id = str(uuid.uuid4())
    result = _compressor.compress(
        context=request.context,
        max_tokens=request.max_tokens,
        query=request.query,
        strategy=request.strategy,
    )
    tracer = ExecutionTracer()
    tracer.start_trace(
        request_id=request_id,
        user_id=int(user_id) if user_id.isdigit() else 0,
        user_message="compress",
    )
    tracer.trace_context_compression(
        request_id=request_id,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        strategy=result.strategy.value,
    )
    tracer.end_trace(request_id, result.compressed)
    return {
        "request_id": request_id,
        "compressed": result.compressed,
        "original_tokens": result.original_tokens,
        "compressed_tokens": result.compressed_tokens,
        "strategy": result.strategy.value,
        "metadata": result.metadata,
    }


@router.post("/compression/extract")
async def extract_important(
    request: ExtractImportantRequest,
    user_id: str = Depends(get_user_id_from_token),
):
    extracted = _compressor.extract_important(
        context=request.context,
        query=request.query,
    )
    return {"extracted": extracted}


@router.get("/compression/estimate-tokens")
async def estimate_tokens(text: str):
    tokens = _compressor.estimate_tokens(text)
    return {"text_length": len(text), "estimated_tokens": tokens}


# ---------------------------------------------------------------------------
# Self-correction loop
# ---------------------------------------------------------------------------


@router.post("/self-correction/review")
async def review_response(
    request: SelfCorrectionRequest,
    user_id: str = Depends(get_user_id_from_token),
):
    request_id = str(uuid.uuid4())
    tracer = ExecutionTracer()
    tracer.start_trace(
        request_id=request_id,
        user_id=int(user_id) if user_id.isdigit() else 0,
        user_message="self-correction",
    )

    result = _self_correction.review(
        response=request.response,
        context=request.context,
        request_id=request_id,
    )
    tracer.end_trace(request_id, result.corrected)
    return {
        "request_id": request_id,
        "original": result.original,
        "corrected": result.corrected,
        "confidence": result.confidence,
        "issues": result.issues,
        "passes": result.passes,
        "metadata": result.metadata,
    }
