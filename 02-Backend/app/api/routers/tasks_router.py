"""Async task submission, polling, and cancellation endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.background_workers import BackgroundWorker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SubmitTaskRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class SubmitTaskResponse(BaseModel):
    task_id: str
    status: str = "pending"


class CancelTaskResponse(BaseModel):
    task_id: str
    cancelled: bool


@router.post("/submit", response_model=SubmitTaskResponse)
async def submit_task(request: SubmitTaskRequest):
    task_id = await BackgroundWorker.submit(request.payload)
    return SubmitTaskResponse(task_id=task_id)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    task = BackgroundWorker.get_result(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        payload=task.payload,
        result=task.result,
        error=task.error,
        created_at=task.created_at.isoformat() if task.created_at else None,
        started_at=task.started_at.isoformat() if getattr(task, "started_at", None) else None,
        completed_at=task.completed_at.isoformat() if getattr(task, "completed_at", None) else None,
    )


@router.delete("/{task_id}", response_model=CancelTaskResponse)
async def cancel_task(task_id: str):
    cancelled = BackgroundWorker.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found or not cancellable")
    return CancelTaskResponse(task_id=task_id, cancelled=True)


@router.get("/", response_model=List[TaskStatusResponse])
async def list_tasks(limit: int = Query(50, ge=1, le=200)):
    results = BackgroundWorker.get_results(limit=limit)
    return [
        TaskStatusResponse(
            task_id=t.task_id,
            status=t.status,
            payload=t.payload,
            result=t.result,
            error=t.error,
            created_at=t.created_at.isoformat() if t.created_at else None,
            started_at=t.started_at.isoformat() if getattr(t, "started_at", None) else None,
            completed_at=t.completed_at.isoformat() if getattr(t, "completed_at", None) else None,
        )
        for t in results
    ]