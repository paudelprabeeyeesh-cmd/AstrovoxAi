"""Unified intelligence kernel.

Coordinates context, routing, artifacts, scheduling, agents, cost, and
observability behind a single request lifecycle.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .agents import Agent, AgentRegistry, get_agent_registry
from .artifacts import Artifact, ArtifactRegistry, get_artifact_registry
from .bus import EventBus, get_event_bus
from .context import ContextBlock, ContextEngine, ContextBudget
from .cost import CostManager, get_cost_manager
from .evaluation import Evaluation, record_evaluation
from .observability import Observability, get_observability
from .router import ModelRouter, RoutingDecision, get_model_router
from .scheduler import WorkflowScheduler, get_workflow_scheduler

@dataclass
class KernelRequest:
    goal: str
    workspace_id: str = "default"
    user_id: str = "anonymous"
    modality: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    budget: Optional[ContextBudget] = None


@dataclass
class KernelResponse:
    request_id: str
    ok: bool
    result: Any = None
    error: Optional[str] = None
    decision: Optional[RoutingDecision] = None
    context_blocks: List[ContextBlock] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    evaluation_id: Optional[str] = None
    elapsed_ms: float = 0.0
    cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
            "decision": self.decision.to_dict() if self.decision else None,
            "context_blocks": [b.to_dict() for b in self.context_blocks],
            "artifacts": self.artifacts,
            "evaluation_id": self.evaluation_id,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "cost": round(self.cost, 6),
        }


class IntelligenceKernel:
    """Central facade that orchestrates the rest of the platform."""

    def __init__(
        self,
        *,
        bus: Optional[EventBus] = None,
        context: Optional[ContextEngine] = None,
        router: Optional[ModelRouter] = None,
        artifacts: Optional[ArtifactRegistry] = None,
        cost: Optional[CostManager] = None,
        scheduler: Optional[WorkflowScheduler] = None,
        agents: Optional[AgentRegistry] = None,
        observability: Optional[Observability] = None,
    ) -> None:
        self.bus = bus or get_event_bus()
        self.context_engine = context or ContextEngine()
        self.router = router or get_model_router()
        self.artifacts = artifacts or get_artifact_registry()
        self.cost = cost or get_cost_manager()
        self.scheduler = scheduler or get_workflow_scheduler()
        self.agents = agents or get_agent_registry()
        self.observability = observability or get_observability()

    # ----- request lifecycle ------------------------------------------

    async def handle(
        self,
        request: KernelRequest,
        handler: Callable[[RoutingDecision], Awaitable[Dict[str, Any]]],
    ) -> KernelResponse:
        start = time.time()
        request_id = f"req_{uuid.uuid4().hex[:10]}"
        span = self.observability.tracer.start(
            "kernel.handle",
            request_id=request_id,
            workspace_id=request.workspace_id,
            modality=request.modality,
        )
        try:
            blocks = self.context_engine.build({"request_id": request_id, **request.metadata}, request.budget)
            input_text = self.context_engine.render(blocks) + f"\n\nGoal: {request.goal}"
            estimated_input_tokens = max(1, int(len(input_text.split()) * 1.3))
            estimated_output_tokens = 256

            from .router import RoutingPolicy

            policy = RoutingPolicy(
                user_tier=request.metadata.get("tier", "authenticated"),
                require_capabilities=[],
            )
            decision = self.router.decide(policy, estimated_input_tokens, estimated_output_tokens)
            if decision is None:
                raise RuntimeError("no models available for this request")
            result = await self.router.execute(decision, handler)
            cost = self.cost.estimate_cost(
                estimated_input_tokens,
                estimated_output_tokens,
                model=decision.primary.name,
            )
            self.cost.record(
                request.workspace_id,
                tokens=estimated_input_tokens + estimated_output_tokens,
                cost=cost,
                requests=1,
                model=decision.primary.name,
            )
            artifact = self.artifacts.register(
                Artifact(
                    id=f"art_{uuid.uuid4().hex[:10]}",
                    type=self._artifact_type_for(request.modality),
                    content=result,
                    workspace_id=request.workspace_id,
                    owner_id=request.user_id,
                    metadata={"request_id": request_id},
                )
            )
            evaluation = record_evaluation(
                request_id,
                request.workspace_id,
                response_latency_ms=(time.time() - start) * 1000,
                cost=cost,
                metadata={"model": decision.primary.name},
            )
            self.observability.metrics.inc("kernel.requests")
            self.observability.metrics.observe("kernel.latency_ms", (time.time() - start) * 1000)
            self.observability.slos.record("latency_p95_ms", (time.time() - start) * 1000)
            self.observability.tracer.end(span)
            self.bus.publish(
                "kernel.handled",
                {
                    "request_id": request_id,
                    "model": decision.primary.name,
                    "cost": cost,
                    "elapsed_ms": (time.time() - start) * 1000,
                },
                source="kernel",
            )
            return KernelResponse(
                request_id=request_id,
                ok=True,
                result=result,
                decision=decision,
                context_blocks=blocks,
                artifacts=[artifact.id],
                evaluation_id=evaluation.id,
                elapsed_ms=(time.time() - start) * 1000,
                cost=cost,
            )
        except Exception as exc:
            self.observability.metrics.inc("kernel.errors")
            self.observability.slos.record("error_rate", 1.0)
            self.observability.tracer.end(span, status="error", error=str(exc))
            self.bus.publish(
                "kernel.failed",
                {"request_id": request_id, "error": str(exc)},
                source="kernel",
            )
            return KernelResponse(
                request_id=request_id,
                ok=False,
                error=str(exc),
                elapsed_ms=(time.time() - start) * 1000,
            )

    @staticmethod
    def _artifact_type_for(modality: str):
        from .artifacts import ArtifactType

        return {
            "text": ArtifactType.TEXT,
            "image": ArtifactType.IMAGE,
            "audio": ArtifactType.AUDIO,
            "video": ArtifactType.VIDEO,
            "document": ArtifactType.DOCUMENT,
        }.get(modality, ArtifactType.TEXT)

    # ----- introspection ----------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "artifacts": self.artifacts.stats(),
            "agents": self.agents.list(),
            "metrics": self.observability.metrics.snapshot(),
            "slo": self.observability.slos.compliance(),
            "cost": self.cost.summary(),
            "traces": len(self.observability.tracer._spans),
            "events": len(self.bus.history(limit=10_000)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


_GLOBAL_KERNEL: Optional[IntelligenceKernel] = None


def get_intelligence_kernel() -> IntelligenceKernel:
    global _GLOBAL_KERNEL
    if _GLOBAL_KERNEL is None:
        _GLOBAL_KERNEL = IntelligenceKernel()
    return _GLOBAL_KERNEL