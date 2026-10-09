import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.intelligence.execution_tracer import ExecutionTracer, TraceEventType
from app.model_router_v2 import MultiModelRouter, RoutingRequest, RoutingPolicy, FallbackStrategy
from app.context_compression import ContextCompressor, CompressionStrategy
from app.self_correction import SelfCorrectionLoop
from app.thinking import ThinkingConfig, ReasoningTrace, get_thinking_config
from app.config import settings

logger = logging.getLogger(__name__)


class ReasoningPolicy(str, Enum):
    DIRECT = "direct"
    BALANCED = "balanced"
    DEEP = "deep"
    SELF_CORRECTED = "self_corrected"


@dataclass
class CompressRequest:
    context: str
    max_tokens: int
    query: Optional[str] = None
    strategy: CompressionStrategy = CompressionStrategy.HYBRID


@dataclass
class RouteRequest:
    user_id: Optional[int] = None
    task_type: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    optimize_for: str = "balanced"
    policy: RoutingPolicy = RoutingPolicy.BALANCED
    fallback_strategy: FallbackStrategy = FallbackStrategy.CROSS_PROVIDER
    max_tokens: Optional[int] = None
    requires_vision: bool = False
    requires_function_calling: bool = True
    preferred_model: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class CorrectRequest:
    response: str
    context: Optional[str] = None
    request_id: Optional[str] = None


class LLMGovernanceService:
    def __init__(
        self,
        tracer: Optional[ExecutionTracer] = None,
        multi_model_router: Optional[MultiModelRouter] = None,
        context_compressor: Optional[ContextCompressor] = None,
        self_correction: Optional[SelfCorrectionLoop] = None,
    ) -> None:
        self.tracer = tracer or ExecutionTracer()
        self.multi_model_router = multi_model_router or MultiModelRouter()
        self.multi_model_router.set_tracer(self.tracer)
        self.context_compressor = context_compressor or ContextCompressor()
        self.self_correction = self_correction or SelfCorrectionLoop()

    async def route(self, request: RouteRequest) -> Dict[str, Any]:
        routing_request = RoutingRequest(
            user_id=request.user_id,
            task_type=request.task_type or "general_chat",
            capabilities=request.capabilities,
            optimize_for=request.optimize_for,
            policy=request.policy,
            fallback_strategy=request.fallback_strategy,
            max_tokens=request.max_tokens,
            requires_vision=request.requires_vision,
            requires_function_calling=request.requires_function_calling,
            preferred_model=request.preferred_model,
            trace=self.tracer,
            request_id=request.request_id,
        )
        result = await self.multi_model_router.route(routing_request)
        if not result:
            raise RuntimeError("No suitable model available for routing")
        return {
            "model_id": result.model_id,
            "provider_name": result.provider_name,
            "reason": result.reason,
            "fallback_chain": result.fallback_chain,
            "estimated_cost_usd": result.estimated_cost_usd,
            "estimated_latency_ms": result.estimated_latency_ms,
            "confidence": result.confidence,
            "metadata": result.metadata,
        }

    async def compress(self, request: CompressRequest) -> Dict[str, Any]:
        result = self.context_compressor.compress(
            context=request.context,
            max_tokens=request.max_tokens,
            query=request.query,
            strategy=request.strategy,
        )
        return {
            "compressed": result.compressed,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "strategy": result.strategy.value,
            "metadata": result.metadata,
        }

    async def correct(self, request: CorrectRequest) -> Dict[str, Any]:
        result = self.self_correction.review(
            response=request.response,
            context=request.context,
            request_id=request.request_id,
        )
        return {
            "original": result.original,
            "corrected": result.corrected,
            "confidence": result.confidence,
            "issues": result.issues,
            "passes": result.passes,
            "metadata": result.metadata,
        }

    async def process(
        self,
        user_message: str,
        user_id: Optional[int] = None,
        task_type: Optional[str] = None,
        context: Optional[str] = None,
        reasoning_policy: ReasoningPolicy = ReasoningPolicy.BALANCED,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if request_id is None:
            request_id = str(uuid.uuid4())

        trace = self.tracer.start_trace(
            request_id=request_id,
            user_id=user_id or 0,
            user_message=user_message,
        )

        try:
            routed = await self.route(
                RouteRequest(
                    user_id=user_id,
                    task_type=task_type or "general_chat",
                    request_id=request_id,
                )
            )

            thinking = self._build_thinking(reasoning_policy, request_id)

            compressed_context = context
            if compressed_context and self.context_compressor.estimate_tokens(compressed_context) > 4096:
                compressed = await self.compress(
                    CompressRequest(
                        context=compressed_context,
                        max_tokens=4096,
                        query=user_message,
                    )
                )
                compressed_context = compressed["compressed"]
                self.tracer.trace_context_compression(
                    request_id=request_id,
                    original_tokens=compressed["original_tokens"],
                    compressed_tokens=compressed["compressed_tokens"],
                    strategy=compressed["strategy"],
                )

            thinking.add_step(
                step="route",
                thought=f"Routed to {routed['model_id']} via {routed['reason']}",
                confidence=routed["confidence"],
                metadata={"provider": routed["provider_name"]},
            )

            response_content = f"[simulated] routed={routed['model_id']} context_len={len(compressed_context or '')}"
            thinking.add_step(
                step="generate",
                thought="Generated the response",
                confidence=0.8,
                metadata={"tokens": len(response_content)},
            )

            corrected = await self.correct(
                CorrectRequest(
                    response=response_content,
                    context=compressed_context,
                    request_id=request_id,
                )
            )

            if corrected["issues"]:
                response_content = corrected["corrected"]

            self.tracer.trace_response_generation(
                request_id=request_id,
                format="text",
                tokens=len(response_content),
            )
            self.tracer.end_trace(request_id, response_content)

            return {
                "request_id": request_id,
                "response": response_content,
                "trace_id": request_id,
                "model_used": routed["model_id"],
                "provider": routed["provider_name"],
                "reason": routed["reason"],
                "fallback_chain": routed["fallback_chain"],
                "estimated_cost_usd": routed["estimated_cost_usd"],
                "estimated_latency_ms": routed["estimated_latency_ms"],
                "confidence": routed["confidence"],
                "reasoning_policy": reasoning_policy.value,
                "self_corrected": bool(corrected["issues"]),
                "correction_issues": corrected["issues"],
                "reasoning_steps": thinking.get_summary(),
                "trace": trace.to_dict(),
            }

        except Exception as exc:
            self.tracer.trace_error(request_id, str(exc))
            self.tracer.end_trace(request_id, "")
            raise

    def _build_thinking(self, policy: ReasoningPolicy, request_id: str) -> ThinkingConfig:
        if policy == ReasoningPolicy.DIRECT:
            return get_thinking_config(enabled=False, request_id=request_id)
        if policy == ReasoningPolicy.DEEP:
            return get_thinking_config(enabled=True, effort="high", request_id=request_id)
        if policy == ReasoningPolicy.SELF_CORRECTED:
            return get_thinking_config(enabled=True, effort="high", request_id=request_id)
        return get_thinking_config(enabled=True, effort="medium", request_id=request_id)
