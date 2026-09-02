"""Intelligent model router.

Selects a model for each request based on modality, cost, latency, and
quality, and falls back to alternates when the primary model fails.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from .bus import get_event_bus


class ModelCapability(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    TOOLS = "tools"
    LONG_CONTEXT = "long_context"
    STREAMING = "streaming"
    REASONING = "reasoning"


@dataclass
class ModelSpec:
    name: str
    provider: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    context_window: int
    avg_latency_ms: float
    quality_score: float = 0.7
    capabilities: List[ModelCapability] = field(default_factory=list)
    tier: str = "authenticated"
    enabled: bool = True

    def supports(self, capability: ModelCapability) -> bool:
        return capability in self.capabilities


@dataclass
class RoutingDecision:
    primary: ModelSpec
    fallbacks: List[ModelSpec]
    reason: str
    expected_cost: float
    expected_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary.name,
            "fallbacks": [f.name for f in self.fallbacks],
            "reason": self.reason,
            "expected_cost": round(self.expected_cost, 6),
            "expected_latency_ms": round(self.expected_latency_ms, 2),
        }


class ModelRegistry:
    """Catalog of available models with live metrics."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelSpec] = {}
        self._stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"latency_ms": 0.0, "errors": 0.0, "calls": 0.0}
        )

    def register(self, spec: ModelSpec) -> None:
        self._models[spec.name] = spec

    def get(self, name: str) -> Optional[ModelSpec]:
        return self._models.get(name)

    def list(self) -> List[ModelSpec]:
        return list(self._models.values())

    def record(self, name: str, latency_ms: float, error: bool = False) -> None:
        s = self._stats[name]
        s["calls"] += 1
        if error:
            s["errors"] += 1
        s["latency_ms"] = s["latency_ms"] * 0.8 + latency_ms * 0.2

    def stats(self, name: str) -> Dict[str, float]:
        return dict(self._stats.get(name, {}))


@dataclass
class RoutingPolicy:
    """User-tunable routing constraints."""

    max_cost: float = 0.05
    max_latency_ms: float = 8000.0
    min_quality: float = 0.5
    user_tier: str = "authenticated"
    require_capabilities: List[ModelCapability] = field(default_factory=list)


class ModelRouter:
    """Picks the best model for a request given policy + metrics."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self._lock_proxy: List[Any] = []

    def candidates(self, policy: RoutingPolicy) -> List[ModelSpec]:
        out: List[ModelSpec] = []
        for spec in self.registry.list():
            if not spec.enabled:
                continue
            if spec.tier not in {policy.user_tier, "public", "authenticated", "partner"}:
                continue
            if any(not spec.supports(cap) for cap in policy.require_capabilities):
                continue
            if spec.quality_score < policy.min_quality:
                continue
            out.append(spec)
        return out

    def decide(
        self,
        policy: RoutingPolicy,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> Optional[RoutingDecision]:
        candidates = self.candidates(policy)
        if not candidates:
            return None
        scored: List[Tuple[float, ModelSpec]] = []
        for spec in candidates:
            cost = (
                spec.cost_per_1k_input * estimated_input_tokens / 1000
                + spec.cost_per_1k_output * estimated_output_tokens / 1000
            )
            live_latency = self.registry.stats(spec.name).get("latency_ms") or spec.avg_latency_ms
            # Lower is better, so invert the score
            score = (
                (1.0 - min(cost / max(policy.max_cost, 1e-6), 1.0)) * 0.4
                + (1.0 - min(live_latency / max(policy.max_latency_ms, 1.0), 1.0)) * 0.3
                + spec.quality_score * 0.3
            )
            scored.append((score, spec))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        if not scored:
            return None
        primary_score, primary = scored[0]
        fallbacks = [s for _, s in scored[1:4]]
        expected_cost = (
            primary.cost_per_1k_input * estimated_input_tokens / 1000
            + primary.cost_per_1k_output * estimated_output_tokens / 1000
        )
        return RoutingDecision(
            primary=primary,
            fallbacks=fallbacks,
            reason=f"score={primary_score:.3f}",
            expected_cost=expected_cost,
            expected_latency_ms=primary.avg_latency_ms,
        )

    async def execute(
        self,
        decision: RoutingDecision,
        handler: Callable[[ModelSpec], Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        chain: List[ModelSpec] = [decision.primary, *decision.fallbacks]
        last_error: Optional[str] = None
        for spec in chain:
            start = time.time()
            try:
                result = await handler(spec)
                self.registry.record(spec.name, (time.time() - start) * 1000, error=False)
                get_event_bus().publish(
                    "model.invocation",
                    {"model": spec.name, "ok": True, "latency_ms": (time.time() - start) * 1000},
                    source="kernel.router",
                )
                result.setdefault("model", spec.name)
                return result
            except Exception as exc:
                self.registry.record(spec.name, (time.time() - start) * 1000, error=True)
                last_error = str(exc)
                get_event_bus().publish(
                    "model.invocation",
                    {"model": spec.name, "ok": False, "error": last_error},
                    source="kernel.router",
                )
        raise RuntimeError(f"All model fallbacks failed: {last_error}")


# ---------------------------------------------------------------------------
# Singleton + default seeding
# ---------------------------------------------------------------------------

_GLOBAL_REGISTRY: Optional[ModelRegistry] = None
_GLOBAL_ROUTER: Optional[ModelRouter] = None


def get_model_registry() -> ModelRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        registry = ModelRegistry()
        registry.register(
            ModelSpec(
                name="gpt-4o",
                provider="openai",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                context_window=128_000,
                avg_latency_ms=1500,
                quality_score=0.95,
                capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.IMAGE,
                    ModelCapability.TOOLS,
                    ModelCapability.LONG_CONTEXT,
                    ModelCapability.STREAMING,
                    ModelCapability.REASONING,
                ],
                tier="authenticated",
            )
        )
        registry.register(
            ModelSpec(
                name="gpt-4o-mini",
                provider="openai",
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                context_window=128_000,
                avg_latency_ms=700,
                quality_score=0.82,
                capabilities=[ModelCapability.TEXT, ModelCapability.TOOLS, ModelCapability.STREAMING],
                tier="public",
            )
        )
        registry.register(
            ModelSpec(
                name="claude-3.5-sonnet",
                provider="anthropic",
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                context_window=200_000,
                avg_latency_ms=1800,
                quality_score=0.94,
                capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.IMAGE,
                    ModelCapability.LONG_CONTEXT,
                    ModelCapability.REASONING,
                ],
                tier="authenticated",
            )
        )
        registry.register(
            ModelSpec(
                name="gemini-1.5-pro",
                provider="google",
                cost_per_1k_input=0.00125,
                cost_per_1k_output=0.005,
                context_window=1_000_000,
                avg_latency_ms=2000,
                quality_score=0.88,
                capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.IMAGE,
                    ModelCapability.VIDEO,
                    ModelCapability.AUDIO,
                    ModelCapability.LONG_CONTEXT,
                ],
                tier="authenticated",
            )
        )
        registry.register(
            ModelSpec(
                name="llama-3.1-70b",
                provider="meta",
                cost_per_1k_input=0.0006,
                cost_per_1k_output=0.0006,
                context_window=128_000,
                avg_latency_ms=900,
                quality_score=0.84,
                capabilities=[ModelCapability.TEXT, ModelCapability.TOOLS],
                tier="authenticated",
            )
        )
        _GLOBAL_REGISTRY = registry
    return _GLOBAL_REGISTRY


def get_model_router() -> ModelRouter:
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = ModelRouter(get_model_registry())
    return _GLOBAL_ROUTER