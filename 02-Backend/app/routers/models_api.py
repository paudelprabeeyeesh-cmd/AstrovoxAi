"""
Model orchestration API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core.model_orchestrator import ModelOrchestrator, OrchestrationRequest
from ..core.model_router_core import ModelEndpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])

orchestrator = ModelOrchestrator()


class ModelRegisterRequest(BaseModel):
    name: str = Field(..., max_length=100)
    provider: str = Field(..., max_length=100)
    model_id: str = Field(..., max_length=200)
    latency_ms: float = Field(100.0, ge=0.0)
    error_rate: float = Field(0.0, ge=0.0, le=1.0)
    cost_per_1k_tokens: float = Field(0.0, ge=0.0)
    max_context: int = Field(4096, ge=1)
    capabilities: List[str] = Field(default_factory=lambda: ["chat", "completion"])
    priority: int = Field(1, ge=1)


class OrchestrateRequest(BaseModel):
    request_id: str = Field(..., max_length=100)
    capabilities: List[str] = Field(default_factory=lambda: ["chat", "completion"])
    max_context: int = Field(4096, ge=1)
    budget_per_1k: Optional[float] = Field(None, ge=0.0)
    latency_target_ms: Optional[float] = Field(None, ge=0.0)
    quality_target: Optional[float] = Field(None, ge=0.0, le=1.0)
    preferred_provider: Optional[str] = Field(None, max_length=100)
    retries: int = Field(3, ge=0, le=10)
    timeout_ms: float = Field(30000.0, ge=0.0)


class OrchestrateResponse(BaseModel):
    request_id: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: int
    success: bool
    error: Optional[str] = None
    fallback_used: bool = False


@router.post("/register")
async def register_model(request: ModelRegisterRequest):
    endpoint = ModelEndpoint(
        name=request.name,
        provider=request.provider,
        model_id=request.model_id,
        latency_ms=request.latency_ms,
        error_rate=request.error_rate,
        cost_per_1k_tokens=request.cost_per_1k_tokens,
        max_context=request.max_context,
        capabilities=request.capabilities,
        priority=request.priority,
    )
    orchestrator.register_endpoint(endpoint)
    return {"status": "OK", "registered": request.name}


@router.post("/orchestrate")
async def orchestrate_request(request: OrchestrateRequest, user_id: str = "anonymous"):
    def runner(endpoint: ModelEndpoint) -> Dict[str, Any]:
        from ..core.llm import LLMClient
        client = LLMClient()
        return client.generate("Hello", timeout=request.timeout_ms / 1000.0)

    orchestration_request = OrchestrationRequest(
        request_id=request.request_id,
        capabilities=request.capabilities,
        max_context=request.max_context,
        budget_per_1k=request.budget_per_1k,
        latency_target_ms=request.latency_target_ms,
        quality_target=request.quality_target,
        preferred_provider=request.preferred_provider,
        retries=request.retries,
        timeout_ms=request.timeout_ms,
    )
    result = orchestrator.dispatch(orchestration_request, runner)
    return OrchestrateResponse(
        request_id=result.request_id,
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
        tokens_used=result.tokens_used,
        success=result.success,
        error=result.error,
        fallback_used=result.fallback_used,
    )


@router.get("/stats")
async def get_model_stats():
    return orchestrator.get_stats()


@router.post("/fallback-chain")
async def set_fallback_chain(chain: List[str]):
    orchestrator.set_fallback_chain(chain)
    return {"status": "OK", "chain": chain}
