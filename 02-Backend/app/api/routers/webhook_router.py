"""Webhook delivery and management endpoints."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.webhooks import webhook_service, DeliveryStatus, WebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookRegisterRequest(BaseModel):
    event_type: str = Field(..., description="Event type to dispatch")
    target_url: str = Field(..., description="Receiver URL")
    payload: dict = Field(default_factory=dict)
    secret: str = Field(default="", description="HMAC secret for signature verification")
    max_attempts: int = Field(default=5, ge=1, le=10)


class WebhookRegisterResponse(BaseModel):
    event_id: str
    status: str


class WebhookDeliveryResponse(BaseModel):
    event_id: str
    status: str
    attempts: int
    last_error: str | None = None


@router.post("/dispatch", response_model=WebhookRegisterResponse)
async def dispatch_webhook(request: WebhookRegisterRequest):
    import uuid
    event = WebhookEvent(
        event_id=str(uuid.uuid4()),
        event_type=request.event_type,
        payload=request.payload,
        target_url=request.target_url,
        secret=request.secret or None,
        max_attempts=request.max_attempts,
    )
    webhook_service.register(event)
    return WebhookRegisterResponse(event_id=event.event_id, status=event.status.value)


@router.post("/{event_id}/deliver", response_model=WebhookDeliveryResponse)
async def deliver_webhook(event_id: str):
    try:
        event = await webhook_service.deliver(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WebhookDeliveryResponse(
        event_id=event.event_id,
        status=event.status.value,
        attempts=event.attempts,
        last_error=event.last_error,
    )


@router.get("/events", response_model=List[WebhookDeliveryResponse])
async def list_webhook_events(status: str | None = None):
    status_enum = None
    if status:
        try:
            status_enum = DeliveryStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from exc
    events = webhook_service.list_events(status=status_enum)
    return [
        WebhookDeliveryResponse(
            event_id=e.event_id,
            status=e.status.value,
            attempts=e.attempts,
            last_error=e.last_error,
        )
        for e in events
    ]


@router.post("/retry-failed")
async def retry_failed_webhooks():
    results = await webhook_service.retry_failed()
    return {"retried": len(results), "results": [{"event_id": r.event_id, "status": r.status.value} for r in results]}
