"""Job and Event API endpoints."""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from .auth_utils import get_user_id_from_token
from .jobs import job_queue, JobPriority, JobStatus
from .events import event_bus

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class SubmitJobRequest(BaseModel):
    type: str
    payload: dict
    priority: Optional[str] = "normal"


@router.post("/")
async def submit_job(request: SubmitJobRequest, authorization: str = Header(None)):
    """Submit a background job."""
    get_user_id_from_token(authorization)

    priority_map = {
        "low": JobPriority.LOW,
        "normal": JobPriority.NORMAL,
        "high": JobPriority.HIGH,
        "critical": JobPriority.CRITICAL,
    }
    priority = priority_map.get(request.priority, JobPriority.NORMAL)

    job_id = await job_queue.submit(
        job_type=request.type,
        payload=request.payload,
        priority=priority,
    )

    return {"status": "OK", "job_id": job_id}


@router.get("/{job_id}")
async def get_job(job_id: str, authorization: str = Header(None)):
    """Get job status."""
    get_user_id_from_token(authorization)

    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return {
        "status": "OK",
        "job": {
            "id": job.id,
            "type": job.type,
            "status": job.status.value,
            "priority": job.priority.value,
            "progress": job.progress,
            "retry_count": job.retry_count,
            "error": job.error,
            "result": job.result,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        },
    }


@router.get("/")
async def list_jobs(
    authorization: str = Header(None),
    status: Optional[str] = None,
    limit: int = 20,
):
    """List jobs."""
    get_user_id_from_token(authorization)

    job_status = JobStatus(status) if status else None
    jobs = job_queue.list_jobs(status=job_status, limit=limit)

    return {
        "status": "OK",
        "jobs": [
            {
                "id": j.id,
                "type": j.type,
                "status": j.status.value,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
    }


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, authorization: str = Header(None)):
    """Cancel a pending job."""
    get_user_id_from_token(authorization)

    if await job_queue.cancel(job_id):
        return {"status": "OK", "message": "Job cancelled"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel job")


@router.get("/stats/overview")
async def job_stats(authorization: str = Header(None)):
    """Get job queue statistics."""
    get_user_id_from_token(authorization)
    return {"status": "OK", "stats": job_queue.get_stats()}


@router.get("/dead-letter/list")
async def list_dead_letter(authorization: str = Header(None)):
    """List dead-lettered jobs."""
    get_user_id_from_token(authorization)
    jobs = job_queue.get_dead_letter()
    return {
        "status": "OK",
        "jobs": [
            {
                "id": j.id,
                "type": j.type,
                "error": j.error,
                "retry_count": j.retry_count,
            }
            for j in jobs
        ],
    }


@router.post("/dead-letter/{job_id}/retry")
async def retry_dead_letter(job_id: str, authorization: str = Header(None)):
    """Retry a dead-lettered job."""
    get_user_id_from_token(authorization)

    if await job_queue.retry_dead_letter(job_id):
        return {"status": "OK", "message": "Job requeued"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found in dead letter")


# ============================================================================
# Events endpoints
# ============================================================================

events_router = APIRouter(prefix="/api/events", tags=["events"])


@events_router.get("/")
async def list_events(
    authorization: str = Header(None),
    event_type: str = "",
    limit: int = 50,
):
    """List recent events."""
    get_user_id_from_token(authorization)
    events = event_bus.get_events(event_type=event_type, limit=limit)
    return {
        "status": "OK",
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "data": e.data,
                "timestamp": e.timestamp,
                "source": e.source,
            }
            for e in events
        ],
    }


@events_router.get("/types")
async def list_event_types(authorization: str = Header(None)):
    """List event types with subscriber counts."""
    get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "types": [
            {"type": t, "subscribers": event_bus.get_subscriber_count(t)}
            for t in event_bus.event_types
        ],
    }
