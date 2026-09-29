"""FastAPI REST API for GPU scheduler."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from models.llm.scheduler.elastic import (
    CostOptimizer,
    ScalingPolicy,
    ScalingPolicyConfig,
    ElasticScaler,
)
from models.llm.scheduler.failover import (
    FailoverManager,
    HealthCheckResult,
    HealthStatus,
    RecoveryStrategy,
)
from models.llm.scheduler.gpu import (
    GPUNode,
    GPUPool,
    GPUResourceError,
    HealthStatus as GPUHealthStatus,
)
from models.llm.scheduler.queue import (
    FairShareScheduler,
    Job,
    JobPriority,
    JobStatus,
    JobQueue,
    PreemptionPolicy,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="AstrovoxAI GPU Scheduler", version="1.0.0")

_pool = GPUPool()
_queue = JobQueue()
_scheduler = FairShareScheduler(_queue)
_failover = FailoverManager()
_elastic = ElasticScaler()
_cost = CostOptimizer()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class JobSubmitRequest(BaseModel):
    name: str = ""
    priority: JobPriority = JobPriority.NORMAL
    required_gpus: int = Field(ge=1, default=1)
    required_memory_mb: int = Field(ge=0, default=0)
    max_runtime_seconds: float = Field(ge=0, default=0.0)
    tenant_id: str = "default"
    preemptible: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    name: str
    priority: str
    status: str
    required_gpus: int
    required_memory_mb: int
    tenant_id: str
    assigned_node: str | None
    created_at: float
    started_at: float | None
    finished_at: float | None


class GPUResponse(BaseModel):
    node_id: str
    gpu_type: str
    gpu_index: int
    memory_total_mb: int
    memory_free_mb: int
    health: str
    running_jobs: int


class ScalingRequest(BaseModel):
    policy: ScalingPolicy = ScalingPolicy.QUEUE_DEPTH
    target_nodes: int = Field(ge=1)
    min_nodes: int = Field(ge=1, default=1)
    max_nodes: int = Field(ge=1, default=10)
    cool_down_seconds: float = Field(ge=0, default=60.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        name=job.name,
        priority=job.priority.value,
        status=job.status.value,
        required_gpus=job.required_gpus,
        required_memory_mb=job.required_memory_mb,
        tenant_id=job.tenant_id,
        assigned_node=job.assigned_node,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _gpu_to_response(node: GPUNode) -> GPUResponse:
    return GPUResponse(
        node_id=node.node_id,
        gpu_type=node.gpu_type,
        gpu_index=node.gpu_index,
        memory_total_mb=node.memory_total_mb,
        memory_free_mb=node.memory_free_mb,
        health=node.health.value,
        running_jobs=len(node.running_jobs),
    )


# ---------------------------------------------------------------------------
# Job endpoints
# ---------------------------------------------------------------------------
@app.post("/jobs", response_model=JobResponse)
def submit_job(req: JobSubmitRequest) -> JobResponse:
    job = Job(
        name=req.name,
        priority=req.priority,
        required_gpus=req.required_gpus,
        required_memory_mb=req.required_memory_mb,
        max_runtime_seconds=req.max_runtime_seconds,
        tenant_id=req.tenant_id,
        preemptible=req.preemptible,
        payload=req.payload,
    )
    _queue.enqueue(job)
    logger.info("Submitted job %s", job.job_id)
    return _job_to_response(job)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = _queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@app.delete("/jobs/{job_id}", response_model=JobResponse)
def cancel_job(job_id: str) -> JobResponse:
    job = _queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.now(timezone.utc).timestamp()
    return _job_to_response(job)


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(status: str | None = None, tenant_id: str | None = None) -> list[JobResponse]:
    jobs: list[Job] = []
    with _queue._lock:
        jobs = list(_queue._by_id.values())
    if status:
        try:
            target = JobStatus(status)
            jobs = [j for j in jobs if j.status == target]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter")
    if tenant_id:
        jobs = [j for j in jobs if j.tenant_id == tenant_id]
    return [_job_to_response(j) for j in jobs]


# ---------------------------------------------------------------------------
# GPU endpoints
# ---------------------------------------------------------------------------
@app.post("/gpus", response_model=GPUResponse)
def register_gpu(node: GPUNode) -> GPUResponse:
    _pool.add_node(node)
    _failover.register_node(node.node_id)
    return _gpu_to_response(node)


@app.get("/gpus", response_model=list[GPUResponse])
def list_gpus() -> list[GPUResponse]:
    return [_gpu_to_response(n) for n in _pool.list_nodes()]


@app.get("/gpus/{node_id}", response_model=GPUResponse)
def get_gpu(node_id: str) -> GPUResponse:
    node = _pool.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="GPU node not found")
    return _gpu_to_response(node)


@app.delete("/gpus/{node_id}")
def remove_gpu(node_id: str) -> dict[str, str]:
    if not _pool.get_node(node_id):
        raise HTTPException(status_code=404, detail="GPU node not found")
    _pool.remove_node(node_id)
    return {"detail": "removed"}


# ---------------------------------------------------------------------------
# Health / failover
# ---------------------------------------------------------------------------
@app.post("/health/check/{node_id}", response_model=HealthCheckResult)
def check_node_health(node_id: str) -> HealthCheckResult:
    result = _failover.check_node(node_id)
    return result


@app.get("/health/nodes", response_model=list[str])
def unhealthy_nodes() -> list[str]:
    return _failover._health.unhealthy_nodes()


@app.post("/failover/{node_id}")
def trigger_failover(node_id: str, job_id: str | None = None) -> dict[str, str]:
    action = _failover.handle_failure(node_id, job_id)
    return {"action": action, "node_id": node_id}


# ---------------------------------------------------------------------------
# Scaling
# ---------------------------------------------------------------------------
@app.post("/scaling/policy", response_model=dict[str, Any])
def set_scaling_policy(req: ScalingRequest) -> dict[str, Any]:
    config = ScalingPolicyConfig(
        policy=req.policy,
        min_nodes=req.min_nodes,
        max_nodes=req.max_nodes,
        cool_down_seconds=req.cool_down_seconds,
    )
    global _elastic
    _elastic = ElasticScaler(config)
    return {"policy": req.policy.value, "current_nodes": _elastic.current_nodes()}


@app.post("/scaling/evaluate", response_model=dict[str, Any])
def evaluate_scaling(metrics: dict[str, Any]) -> dict[str, Any]:
    return _elastic.evaluate(metrics)


@app.post("/scaling/nodes", response_model=dict[str, int])
def set_node_count(count: int) -> dict[str, int]:
    _elastic.set_nodes(count)
    return {"nodes": _elastic.current_nodes()}


@app.get("/scaling/status", response_model=dict[str, Any])
def scaling_status() -> dict[str, Any]:
    return {"current_nodes": _elastic.current_nodes()}


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------
@app.get("/cost/estimate")
def cost_estimate(instance_type: str, hours: float) -> dict[str, Any]:
    cost = _cost.estimate_cost(instance_type, hours)
    return {"instance_type": instance_type, "hours": hours, "estimated_cost_usd": cost}


@app.post("/cost/recommend", response_model=dict[str, Any])
def cost_recommend(
    current_nodes: int,
    queue_depth: int,
    avg_runtime_seconds: float,
) -> dict[str, Any]:
    return _cost.recommend_scale(current_nodes, queue_depth, avg_runtime_seconds)
