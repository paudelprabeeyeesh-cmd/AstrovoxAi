"""FastAPI router exposing the Intelligence Kernel."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth_utils import get_current_user
from .agents import AgentSpec, get_agent_registry
from .artifacts import Artifact, ArtifactType, get_artifact_registry
from .bus import get_event_bus
from .context import ContextBudget, ContextEngine
from .cost import Quota, get_cost_manager
from .evaluation import get_evaluation_store
from .observability import SLODefinition, get_observability
from .router import RoutingPolicy, get_model_registry, get_model_router
from .scheduler import DAG, Job, get_workflow_scheduler

router = APIRouter(prefix="/kernel", tags=["kernel"])


# ---- Kernel handle --------------------------------------------------------


class KernelHandleRequest(BaseModel):
    goal: str
    workspace_id: str = "default"
    modality: str = "text"
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = 8000
    reserve_for_response: int = 1024


@router.post("/handle")
async def kernel_handle(
    req: KernelHandleRequest, user=Depends(get_current_user)
) -> Dict[str, Any]:
    kernel = get_intelligence_kernel()
    budget = ContextBudget(max_tokens=req.max_tokens, reserve_for_response=req.reserve_for_response)

    async def _handler(decision):  # type: ignore[no-untyped-def]
        return {
            "model": decision.name,
            "provider": decision.provider,
            "response": f"[{decision.name}] echo: {req.goal[:200]}",
        }

    from . import KernelRequest

    response = await kernel.handle(
        KernelRequest(
            goal=req.goal,
            workspace_id=req.workspace_id,
            user_id=req.user_id or user.get("id", "anonymous"),
            modality=req.modality,
            metadata=req.metadata,
            budget=budget,
        ),
        _handler,
    )
    return response.to_dict()


@router.get("/status")
async def kernel_status() -> Dict[str, Any]:
    return get_intelligence_kernel().status()


# ---- Event bus ------------------------------------------------------------


@router.get("/events")
async def kernel_events(topic: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    return {"events": get_event_bus().history(topic, limit)}


# ---- Models / routing -----------------------------------------------------


class RoutingPolicyRequest(BaseModel):
    max_cost: float = 0.05
    max_latency_ms: float = 8000.0
    min_quality: float = 0.5
    user_tier: str = "authenticated"
    require_capabilities: List[str] = Field(default_factory=list)


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    return {
        "models": [
            {
                "name": m.name,
                "provider": m.provider,
                "cost_per_1k_input": m.cost_per_1k_input,
                "cost_per_1k_output": m.cost_per_1k_output,
                "context_window": m.context_window,
                "avg_latency_ms": m.avg_latency_ms,
                "quality_score": m.quality_score,
                "capabilities": [c.value for c in m.capabilities],
                "tier": m.tier,
            }
            for m in get_model_registry().list()
        ]
    }


@router.post("/models/select")
async def select_model(
    policy: RoutingPolicyRequest,
    input_tokens: int = 1000,
    output_tokens: int = 256,
) -> Dict[str, Any]:
    from .router import ModelCapability

    caps = [ModelCapability(c) for c in policy.require_capabilities if c]
    try:
        decision = get_model_router().decide(
            RoutingPolicy(
                max_cost=policy.max_cost,
                max_latency_ms=policy.max_latency_ms,
                min_quality=policy.min_quality,
                user_tier=policy.user_tier,
                require_capabilities=caps,
            ),
            input_tokens,
            output_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if decision is None:
        raise HTTPException(status_code=404, detail="no models match policy")
    return decision.to_dict()


# ---- Artifacts ------------------------------------------------------------


class ArtifactRegisterRequest(BaseModel):
    type: str
    content: Any
    workspace_id: str = "default"
    owner_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None
    mime_type: str = "application/octet-stream"


@router.post("/artifacts")
async def register_artifact(
    req: ArtifactRegisterRequest, user=Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        atype = ArtifactType(req.type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    artifact = Artifact(
        id=f"art_{__import__('uuid').uuid4().hex[:10]}",
        type=atype,
        content=req.content,
        owner_id=req.owner_id or user.get("id", "anonymous"),
        workspace_id=req.workspace_id,
        metadata=req.metadata,
        parent_id=req.parent_id,
        mime_type=req.mime_type,
    )
    get_artifact_registry().register(artifact)
    return artifact.to_dict()


@router.get("/artifacts")
async def list_artifacts(
    type: Optional[str] = None, workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    atype = ArtifactType(type) if type else None
    artifacts = get_artifact_registry().list(atype, workspace_id)
    return {"count": len(artifacts), "artifacts": [a.to_dict() for a in artifacts]}


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str) -> Dict[str, Any]:
    artifact = get_artifact_registry().get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {"artifact": artifact.to_dict(), "lineage": [
        a.to_dict() for a in get_artifact_registry().lineage(artifact_id)
    ]}


# ---- Workflows / DAGs -----------------------------------------------------


class WorkflowJobRequest(BaseModel):
    name: str
    depends_on: List[str] = Field(default_factory=list)
    priority: int = 5
    timeout_seconds: float = 30.0
    max_retries: int = 0
    requires_approval: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    handler: str = "echo"  # symbolic handler name; resolved at runtime


class WorkflowRunRequest(BaseModel):
    jobs: List[WorkflowJobRequest]


@router.post("/workflows/run")
async def workflow_run(req: WorkflowRunRequest) -> Dict[str, Any]:
    dag = DAG()
    handlers = _handler_registry()
    for jr in req.jobs:
        handler = handlers.get(jr.handler)
        if handler is None:
            raise HTTPException(status_code=400, detail=f"unknown handler: {jr.handler}")
        dag.add(
            Job(
                id=f"job_{__import__('uuid').uuid4().hex[:10]}",
                name=jr.name,
                depends_on=jr.depends_on,
                priority=jr.priority,
                timeout_seconds=jr.timeout_seconds,
                max_retries=jr.max_retries,
                requires_approval=jr.requires_approval,
                metadata=jr.metadata,
                handler=handler,
            )
        )
    scheduler = get_workflow_scheduler()
    scheduler.load(dag)
    return await scheduler.run()


@router.post("/workflows/approve/{job_id}")
async def workflow_approve(job_id: str) -> Dict[str, Any]:
    return {"approved": get_workflow_scheduler().approve(job_id)}


@router.post("/workflows/cancel/{job_id}")
async def workflow_cancel(job_id: str) -> Dict[str, Any]:
    return {"cancelled": get_workflow_scheduler().cancel(job_id)}


def _handler_registry() -> Dict[str, Any]:
    async def _echo(job: Job) -> Dict[str, Any]:
        return {"echo": job.name, "metadata": job.metadata}

    async def _fail(job: Job) -> Dict[str, Any]:
        raise RuntimeError(f"intentional failure for {job.name}")

    return {"echo": _echo, "fail": _fail}


# ---- Agents ---------------------------------------------------------------


class AgentRegisterRequest(BaseModel):
    name: str
    role: str
    description: str = ""
    tools: List[str] = Field(default_factory=list)
    max_iterations: int = 5


@router.post("/agents")
async def register_agent(
    req: AgentRegisterRequest, user=Depends(get_current_user)
) -> Dict[str, Any]:
    from .agents import Agent

    agent = Agent(AgentSpec(**req.dict()))
    get_agent_registry().register(agent)
    return {"id": agent.id, "name": agent.spec.name}


@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    return {"agents": get_agent_registry().list()}


class AgentRunRequest(BaseModel):
    name: str
    goal: str


@router.post("/agents/run")
async def run_agent(req: AgentRunRequest) -> Dict[str, Any]:
    matches = get_agent_registry().by_name(req.name)
    if not matches:
        raise HTTPException(status_code=404, detail="agent not found")
    return await matches[0].run(req.goal)


# ---- Cost -----------------------------------------------------------------


class QuotaRequest(BaseModel):
    requests: int = 1000
    tokens: int = 4_000_000
    cost: float = 50.0
    storage_bytes: int = 50_000_000_000


@router.post("/quotas/{workspace_id}")
async def set_quota(workspace_id: str, req: QuotaRequest) -> Dict[str, Any]:
    get_cost_manager().set_quota(workspace_id, Quota(**req.dict()))
    return {"ok": True}


@router.get("/quotas/{workspace_id}")
async def get_quota(workspace_id: str) -> Dict[str, Any]:
    return get_cost_manager().check_quota(workspace_id)


@router.get("/costs")
async def cost_summary() -> Dict[str, Any]:
    return get_cost_manager().summary()


# ---- Evaluations ----------------------------------------------------------


@router.get("/evaluations")
async def list_evaluations(workspace_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    items = get_evaluation_store().list(workspace_id, limit)
    return {"count": len(items), "evaluations": [e.to_dict() for e in items]}


@router.get("/evaluations/summary")
async def evaluation_summary(workspace_id: Optional[str] = None) -> Dict[str, Any]:
    return get_evaluation_store().summary(workspace_id)


# ---- Observability --------------------------------------------------------


class SLODefinitionRequest(BaseModel):
    name: str
    threshold: float
    comparator: str = "lt"
    description: str = ""


@router.post("/slo")
async def define_slo(req: SLODefinitionRequest) -> Dict[str, Any]:
    get_observability().slos.define(SLODefinition(**req.dict()))
    return {"ok": True}


@router.get("/slo")
async def slo_status() -> Dict[str, Any]:
    return get_observability().slos.compliance()


@router.get("/metrics")
async def metrics_snapshot() -> Dict[str, Any]:
    return get_observability().metrics.snapshot()


@router.get("/traces")
async def traces_recent(limit: int = 100) -> Dict[str, Any]:
    return {"traces": get_observability().tracer.recent(limit)}


# ---- Context engine utilities ---------------------------------------------


class ContextBuildRequest(BaseModel):
    system: str = ""
    instruction: str = ""
    history: List[Dict[str, Any]] = Field(default_factory=list)
    memories: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval: List[Dict[str, Any]] = Field(default_factory=list)
    tool_outputs: List[Dict[str, Any]] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = 4000


@router.post("/context/build")
async def build_context(req: ContextBuildRequest) -> Dict[str, Any]:
    from .context import (
        history_source,
        instruction_source,
        memory_source,
        preferences_source,
        retrieval_source,
        system_source,
        tool_source,
    )

    engine = ContextEngine()
    if req.system:
        engine.register_source(system_source(req.system))
    if req.instruction:
        engine.register_source(instruction_source(req.instruction))
    if req.history:
        engine.register_source(history_source(req.history))
    if req.memories:
        engine.register_source(memory_source(req.memories))
    if req.retrieval:
        engine.register_source(retrieval_source(req.retrieval))
    if req.tool_outputs:
        engine.register_source(tool_source(req.tool_outputs))
    if req.preferences:
        engine.register_source(preferences_source(req.preferences))
    blocks = engine.build(
        {"request_id": "ctx"},
        ContextBudget(max_tokens=req.max_tokens, reserve_for_response=256),
    )
    return {
        "blocks": [b.to_dict() for b in blocks],
        "rendered": engine.render(blocks),
    }