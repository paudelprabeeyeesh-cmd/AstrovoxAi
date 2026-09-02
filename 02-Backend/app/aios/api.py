"""FastAPI surface for the AIOS operating system."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth_utils import get_current_user

from .consensus import Node, get_consensus
from .healing import HealthProbe, get_self_healing
from .memory import MemoryTier, get_memory_manager
from .mesh import ServiceInstance, ServiceState, get_service_registry, seed_default_services
from .observability import SLO, get_aios_observability
from .resources import ResourceUsage, get_resource_manager
from .runtime import DelegationRequest, get_ai_runtime
from .scheduler import Job, get_distributed_scheduler
from .search import SearchDocument, SearchModality, get_universal_search
from .security import (
    Policy,
    PolicyAction,
    SecurityContext,
    get_security_layer,
)

router = APIRouter(prefix="/aios", tags=["aios"])


# ---- Service mesh ---------------------------------------------------------


class ServiceRegisterRequest(BaseModel):
    name: str
    version: str = "1.0.0"
    host: str
    port: int
    region: str = "default"
    zone: str = "default"
    weight: int = 100
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/services")
async def register_service(req: ServiceRegisterRequest) -> Dict[str, Any]:
    instance = ServiceInstance(
        id="",
        name=req.name,
        version=req.version,
        host=req.host,
        port=req.port,
        region=req.region,
        zone=req.zone,
        weight=req.weight,
        metadata=req.metadata,
    )
    get_service_registry().register(instance)
    return instance.to_dict()


@router.get("/services")
async def list_services(name: Optional[str] = None) -> Dict[str, Any]:
    registry = get_service_registry()
    if name:
        return {"services": [i.to_dict() for i in registry.discover(name)]}
    return {"services": registry.list(), "stats": registry.stats()}


@router.get("/services/pick")
async def pick_service(name: str) -> Dict[str, Any]:
    inst = get_service_registry().pick(name)
    if inst is None:
        raise HTTPException(status_code=404, detail="no healthy instances")
    return inst.to_dict()


@router.post("/services/heartbeat/{instance_id}")
async def heartbeat(instance_id: str) -> Dict[str, Any]:
    return {"ok": get_service_registry().heartbeat(instance_id)}


@router.post("/services/health-check")
async def run_health_checks() -> Dict[str, Any]:
    return {"results": get_service_registry().run_health_checks()}


@router.post("/services/seed")
async def seed() -> Dict[str, Any]:
    seed_default_services()
    return {"ok": True, "stats": get_service_registry().stats()}


# ---- Memory tiers ---------------------------------------------------------


class MemoryPutRequest(BaseModel):
    key: str
    value: Any
    tier: str = "hot"
    ttl: Optional[float] = None
    compress: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/memory")
async def memory_put(req: MemoryPutRequest) -> Dict[str, Any]:
    tier = MemoryTier(req.tier)
    record = get_memory_manager().put(
        req.key,
        req.value,
        tier=tier,
        ttl=req.ttl,
        compress=req.compress,
        **req.metadata,
    )
    return record.to_dict()


@router.get("/memory/{key}")
async def memory_get(key: str) -> Dict[str, Any]:
    record = get_memory_manager().get(key)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    return record.to_dict()


@router.post("/memory/{key}/promote")
async def memory_promote(key: str, target: str) -> Dict[str, Any]:
    return (get_memory_manager().promote(key, MemoryTier(target)) or {}).to_dict() if get_memory_manager().get(key) else {"ok": False}


@router.get("/memory")
async def memory_snapshot() -> Dict[str, Any]:
    return get_memory_manager().snapshot()


# ---- Scheduler ------------------------------------------------------------


class JobRequest(BaseModel):
    name: str
    depends_on: List[str] = Field(default_factory=list)
    priority: int = 5
    timeout_seconds: float = 30.0
    max_retries: int = 0
    resource_hint: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    handler: str = "echo"


@router.post("/scheduler/jobs")
async def submit_job(req: JobRequest) -> Dict[str, Any]:
    handler = _handler(req.handler)
    job = Job(
        id="",
        name=req.name,
        depends_on=req.depends_on,
        priority=req.priority,
        timeout_seconds=req.timeout_seconds,
        max_retries=req.max_retries,
        resource_hint=req.resource_hint,
        metadata=req.metadata,
        handler=handler,
    )
    return get_distributed_scheduler().submit(job).to_dict()


@router.get("/scheduler/status")
async def scheduler_status() -> Dict[str, Any]:
    return get_distributed_scheduler().status()


@router.post("/scheduler/run")
async def scheduler_run(deadline_s: float = 30.0) -> Dict[str, Any]:
    import asyncio
    return await get_distributed_scheduler().run(deadline_s=deadline_s)


def _handler(name: str):
    async def _echo(job: Job) -> Dict[str, Any]:
        return {"ok": True, "job": job.name, "metadata": job.metadata}

    async def _fail(job: Job) -> Dict[str, Any]:
        raise RuntimeError(f"intentional failure for {job.name}")

    return {"echo": _echo, "fail": _fail}.get(name, _echo)


# ---- AI runtime -----------------------------------------------------------


class AgentRegisterRequest(BaseModel):
    name: str
    role: str
    max_concurrent: int = 4
    max_tasks_per_minute: int = 120
    max_tokens_per_minute: int = 200_000
    tools: List[str] = Field(default_factory=list)


@router.post("/runtime/agents")
async def register_agent(req: AgentRegisterRequest) -> Dict[str, Any]:
    agent = get_ai_runtime().register_agent(
        name=req.name,
        role=req.role,
        max_concurrent=req.max_concurrent,
        max_tasks_per_minute=req.max_tasks_per_minute,
        max_tokens_per_minute=req.max_tokens_per_minute,
        tools=req.tools,
    )
    return {"id": agent.id, "name": agent.spec.name}


@router.get("/runtime/agents")
async def list_agents() -> Dict[str, Any]:
    return {"agents": get_ai_runtime().registry.list()}


class AgentRunRequest(BaseModel):
    name: str
    goal: str
    tokens: int = 0


@router.post("/runtime/agents/run")
async def run_agent(req: AgentRunRequest) -> Dict[str, Any]:
    return await get_ai_runtime().run_agent(req.name, req.goal, tokens=req.tokens)


@router.get("/runtime/status")
async def runtime_status() -> Dict[str, Any]:
    return get_ai_runtime().status()


class MessageRequest(BaseModel):
    sender: str
    recipient: str
    topic: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/runtime/messages")
async def send_message(req: MessageRequest) -> Dict[str, Any]:
    msg = get_ai_runtime().router.send(req.sender, req.recipient, req.topic, req.payload)
    return msg.to_dict()


@router.get("/runtime/messages/{agent}")
async def agent_inbox(agent: str) -> Dict[str, Any]:
    return {"messages": get_ai_runtime().inbox(agent)}


# ---- Universal search -----------------------------------------------------


class IndexRequest(BaseModel):
    modality: str = "document"
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    doc_id: Optional[str] = None


@router.post("/search/index")
async def search_index(req: IndexRequest) -> Dict[str, Any]:
    doc = SearchDocument(
        id=req.doc_id or "",
        modality=SearchModality(req.modality),
        title=req.title,
        content=req.content,
        metadata=req.metadata,
        embedding=req.embedding,
    )
    indexed = get_universal_search().index(doc)
    return indexed.to_dict()


class SearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    modalities: Optional[List[str]] = None
    limit: int = 10
    semantic_weight: float = 0.5
    lexical_weight: float = 0.4
    personalization_weight: float = 0.1
    embedding: Optional[List[float]] = None


@router.post("/search/query")
async def search_query(req: SearchRequest) -> Dict[str, Any]:
    mods = [SearchModality(m) for m in (req.modalities or [])]
    hits = get_universal_search().search(
        req.query,
        user_id=req.user_id,
        modalities=mods or None,
        limit=req.limit,
        semantic_weight=req.semantic_weight,
        lexical_weight=req.lexical_weight,
        personalization_weight=req.personalization_weight,
        embedding=req.embedding,
    )
    return {"count": len(hits), "hits": [h.to_dict() for h in hits]}


@router.get("/search/stats")
async def search_stats() -> Dict[str, Any]:
    return get_universal_search().stats()


# ---- Resource manager -----------------------------------------------------


class ResourceRecordRequest(BaseModel):
    cpu: float = 0.0
    memory: float = 0.0
    gpu: float = 0.0
    storage: float = 0.0
    tokens_per_min: float = 0.0
    network_mbps: float = 0.0
    queue_depth: int = 0


@router.post("/resources/record")
async def resource_record(req: ResourceRecordRequest) -> Dict[str, Any]:
    usage = ResourceUsage(**req.dict())
    get_resource_manager().record(usage)
    return {"ok": True}


@router.get("/resources/snapshot")
async def resource_snapshot() -> Dict[str, Any]:
    return get_resource_manager().snapshot()


@router.get("/resources/scale")
async def resource_scale() -> Dict[str, Any]:
    return get_resource_manager().scale_all()


# ---- Consensus ------------------------------------------------------------


class NodeAddRequest(BaseModel):
    address: str
    zone: str = "default"
    region: str = "default"
    role: str = "worker"


@router.post("/consensus/nodes")
async def add_node(req: NodeAddRequest) -> Dict[str, Any]:
    import uuid as _uuid
    node = Node(id=f"node_{_uuid.uuid4().hex[:8]}", address=req.address, zone=req.zone, region=req.region, role=req.role)
    get_consensus().membership.add(node)
    return node.to_dict()


@router.get("/consensus/status")
async def consensus_status() -> Dict[str, Any]:
    return get_consensus().status()


class LockRequest(BaseModel):
    key: str
    holder: str
    ttl: float = 5.0


@router.post("/consensus/lock")
async def lock(req: LockRequest) -> Dict[str, Any]:
    ok = get_consensus().locks.acquire(req.key, req.holder, req.ttl)
    return {"acquired": ok}


@router.post("/consensus/lock/release")
async def release_lock(req: LockRequest) -> Dict[str, Any]:
    return {"released": get_consensus().locks.release(req.key, req.holder)}


class ConfigSetRequest(BaseModel):
    key: str
    value: Any


@router.post("/consensus/config")
async def config_set(req: ConfigSetRequest) -> Dict[str, Any]:
    return {"version": get_consensus().config.set(req.key, req.value)}


@router.get("/consensus/config/{key}")
async def config_get(key: str) -> Dict[str, Any]:
    return {"value": get_consensus().config.get(key), "version": get_consensus().config.version(key)}


# ---- Self-healing ---------------------------------------------------------


@router.get("/healing/status")
async def healing_status() -> Dict[str, Any]:
    return get_self_healing().status()


class CircuitRecordRequest(BaseModel):
    name: str
    success: bool


@router.post("/healing/circuit")
async def record_circuit(req: CircuitRecordRequest) -> Dict[str, Any]:
    get_self_healing().circuits.record(req.name, success=req.success)
    return get_self_healing().circuits.breaker(req.name).to_dict()


class RecoveryRequest(BaseModel):
    target: str
    action: str
    reason: str


@router.post("/healing/recover")
async def recover(req: RecoveryRequest) -> Dict[str, Any]:
    return get_self_healing().recover(req.target, req.action, req.reason).to_dict()


# ---- Observability --------------------------------------------------------


@router.get("/observability/status")
async def observability_status() -> Dict[str, Any]:
    return get_aios_observability().status()


class SLODefinitionRequest(BaseModel):
    name: str
    target: float
    comparator: str = "lt"
    window_s: float = 3600.0
    description: str = ""


@router.post("/observability/slo")
async def define_slo(req: SLODefinitionRequest) -> Dict[str, Any]:
    get_aios_observability().define(SLO(**req.dict()))
    return {"ok": True}


@router.get("/observability/slo")
async def slo_status() -> Dict[str, Any]:
    return {"slos": get_aios_observability().slo_status()}


@router.get("/observability/logs")
async def logs(level: Optional[str] = None, service: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    return {"logs": get_aios_observability().logs.search(level=level, service=service, limit=limit)}


@router.get("/observability/traces")
async def traces(limit: int = 50) -> Dict[str, Any]:
    return {"traces": get_aios_observability().traces.recent(limit)}


@router.get("/observability/dependencies")
async def dependencies() -> Dict[str, Any]:
    return get_aios_observability().dependencies.to_dict()


# ---- Security -------------------------------------------------------------


class PolicyRequest(BaseModel):
    name: str
    effect: str = "allow"
    actions: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    principals: List[str] = Field(default_factory=list)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""


@router.post("/security/policies")
async def add_policy(req: PolicyRequest) -> Dict[str, Any]:
    get_security_layer().policy.add(Policy(**req.dict()))
    return {"ok": True}


@router.get("/security/policies")
async def list_policies() -> Dict[str, Any]:
    return {"policies": get_security_layer().policy.list()}


class AuthorizeRequest(BaseModel):
    principal: str
    scopes: List[str] = Field(default_factory=list)
    mTLS: bool = False
    action: str
    resource: str
    workspace: Optional[str] = None


@router.post("/security/authorize")
async def authorize(req: AuthorizeRequest) -> Dict[str, Any]:
    ctx = SecurityContext(req.principal, req.scopes, mTLS=req.mTLS)
    if req.workspace is not None:
        ctx.attributes["workspace"] = req.workspace
    decision = get_security_layer().authorize(ctx, req.action, req.resource, workspace=req.workspace)
    return {"decision": decision.value}


@router.get("/security/audit")
async def audit(limit: int = 50) -> Dict[str, Any]:
    return {"entries": get_security_layer().audit.list(limit)}


class SecretPutRequest(BaseModel):
    name: str
    value: str
    ttl_s: Optional[float] = None


@router.post("/security/secrets")
async def secret_put(req: SecretPutRequest) -> Dict[str, Any]:
    return {"version": get_security_layer().secrets.put(req.name, req.value, ttl_s=req.ttl_s)}


@router.get("/security/secrets/{name}")
async def secret_get(name: str) -> Dict[str, Any]:
    return {"value": get_security_layer().secrets.get(name)}


@router.post("/security/secrets/{name}/rotate")
async def secret_rotate(name: str) -> Dict[str, Any]:
    return {"version": get_security_layer().secrets.rotate(name)}


@router.get("/security/status")
async def security_status() -> Dict[str, Any]:
    return get_security_layer().status()