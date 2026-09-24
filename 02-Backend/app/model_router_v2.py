import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.providers.factory import ProviderFactory
from app.providers.base import ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class RoutingPolicy(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    COST_FIRST = "cost_first"
    SPEED_FIRST = "speed_first"
    QUALITY_FIRST = "quality_first"


class FallbackStrategy(str, Enum):
    NONE = "none"
    SAME_PROVIDER = "same_provider"
    CROSS_PROVIDER = "cross_provider"
    LOCAL_FALLBACK = "local_fallback"


@dataclass
class RoutingRequest:
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
    trace: Any = None
    request_id: Optional[str] = None


@dataclass
class RoutingResult:
    model_id: str
    provider_name: str
    reason: str
    fallback_chain: List[str]
    estimated_cost_usd: float
    estimated_latency_ms: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiModelRouter:
    def __init__(self, orchestrator: Any = None):
        self.orchestrator = orchestrator
        self.tracer: Any = None

    def set_tracer(self, tracer: Any) -> None:
        self.tracer = tracer

    async def route(self, request: RoutingRequest) -> Optional[RoutingResult]:
        candidates = self._build_candidate_chain(request)
        if not candidates:
            return None

        primary = candidates[0]
        fallback_chain = candidates[1:]

        if request.trace and request.request_id:
            try:
                request.trace.trace_model_selection(
                    request_id=request.request_id,
                    model_name=primary,
                    reason=f"Selected primary model for policy={request.policy.value}",
                    alternatives=fallback_chain,
                )
            except Exception:
                pass

        provider = ProviderFactory.get_for_model(primary)
        if not provider:
            fallback = self._select_fallback(request, fallback_chain)
            if fallback:
                return fallback
            return None

        info = None
        try:
            from app.providers.models import get_model_info
            info = get_model_info(primary)
        except Exception:
            pass

        estimated_cost = self._estimate_cost(primary, request.max_tokens or 4096)
        estimated_latency = self._estimate_latency(primary)

        return RoutingResult(
            model_id=primary,
            provider_name=provider.name,
            reason=f"Selected via policy={request.policy.value}",
            fallback_chain=fallback_chain,
            estimated_cost_usd=estimated_cost,
            estimated_latency_ms=estimated_latency,
            confidence=0.9,
            metadata={
                "max_tokens": info.max_tokens if info else 4096,
                "supports_streaming": info.supports_streaming if info else True,
            },
        )

    async def chat_with_fallback(
        self,
        request: RoutingRequest,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        result = await self.route(request)
        if not result:
            raise RuntimeError("No suitable model available for routing")

        primary_model = result.model_id
        fallback_chain = result.fallback_chain
        last_error: Optional[Exception] = None

        for model_id in [primary_model] + fallback_chain:
            provider = ProviderFactory.get_for_model(model_id)
            if not provider:
                continue
            try:
                response = await provider.chat(
                    messages=messages,
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt,
                )
                response.metadata["routed_via"] = "multi_model_router"
                response.metadata["fallback_used"] = model_id != primary_model
                response.metadata["primary_model"] = primary_model
                if request.trace and request.request_id:
                    try:
                        request.trace.trace_model_selection(
                            request_id=request.request_id,
                            model_name=model_id,
                            reason=f"Executed via chat_with_fallback (fallback={model_id != primary_model})",
                            alternatives=fallback_chain,
                        )
                    except Exception:
                        pass
                return response
            except Exception as exc:
                last_error = exc
                logger.warning("Model %s failed: %s", model_id, exc)
                if request.trace and request.request_id:
                    try:
                        request.trace.trace_error(
                            request_id=request.request_id,
                            error=str(exc),
                            context={"model_id": model_id, "stage": "chat_with_fallback"},
                        )
                    except Exception:
                        pass
                continue

        raise RuntimeError(f"All candidate models failed: {last_error}")

    def _build_candidate_chain(self, request: RoutingRequest) -> List[str]:
        orchestrator = self.orchestrator or getattr(request, "orchestrator", None)
        if orchestrator:
            model_config = orchestrator.select_model(
                task_type=request.task_type or "general_chat",
                user_id=request.user_id,
                optimize_for=request.optimize_for,
                max_tokens=request.max_tokens,
                requires_vision=request.requires_vision,
                requires_function_calling=request.requires_function_calling,
            )
            if model_config:
                chain = [model_config.model_name]
                if request.fallback_strategy != FallbackStrategy.NONE:
                    for model_id, cfg in orchestrator.models.items():
                        if model_id != model_config.model_name and cfg.supports_function_calling:
                            chain.append(model_id)
                return chain

        candidates: List[str] = []
        try:
            from app.providers.models import list_models
            for m in list_models():
                if request.requires_vision and not m.supports_vision:
                    continue
                if request.requires_function_calling and not m.supports_function_calling:
                    continue
                candidates.append(m.id)
        except Exception:
            pass

        if request.preferred_model and request.preferred_model in candidates:
            candidates = [request.preferred_model] + [c for c in candidates if c != request.preferred_model]
        return candidates

    def _select_fallback(self, request: RoutingRequest, fallback_chain: List[str]) -> Optional[RoutingResult]:
        for model_id in fallback_chain:
            provider = ProviderFactory.get_for_model(model_id)
            if not provider:
                continue
            try:
                from app.providers.models import get_model_info
                info = get_model_info(model_id)
                return RoutingResult(
                    model_id=model_id,
                    provider_name=provider.name,
                    reason="Primary unavailable; fallback selected",
                    fallback_chain=[],
                    estimated_cost_usd=self._estimate_cost(model_id, request.max_tokens or 4096),
                    estimated_latency_ms=self._estimate_latency(model_id),
                    confidence=0.7,
                    metadata={"max_tokens": info.max_tokens if info else 4096, "supports_streaming": info.supports_streaming if info else True},
                )
            except Exception:
                continue
        return None

    def _estimate_cost(self, model_id: str, tokens: int) -> float:
        if not self.orchestrator:
            return 0.0
        try:
            return self.orchestrator.estimate_cost(model_id, tokens, tokens // 2)
        except Exception:
            return 0.0

    def _estimate_latency(self, model_id: str) -> int:
        if not self.orchestrator:
            return 1000
        info = self.orchestrator.get_model_info(model_id)
        if info:
            return info.get("avg_latency_ms", 1000)
        return 1000
