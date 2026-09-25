"""Webhook delivery service with retries, signing, and dead-letter queue."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from app.dead_letter_queue import DeadLetterQueue, DLQStatus

logger = logging.getLogger("astravox.webhooks")


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"


@dataclass
class WebhookEvent:
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    target_url: str
    secret: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 5
    status: DeliveryStatus = DeliveryStatus.PENDING
    last_error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WebhookDeliveryService:
    """Deliver webhook events with exponential backoff retries and dead-letter queue."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        self._events: Dict[str, WebhookEvent] = {}
        self._dlq = DeadLetterQueue()
        self._lock = asyncio.Lock()

    def register(self, event: WebhookEvent) -> None:
        self._events[event.event_id] = event

    def _sign(self, event: WebhookEvent, body: str) -> str:
        if not event.secret:
            return ""
        return hmac.new(event.secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    async def deliver(self, event_id: str) -> WebhookEvent:
        event = self._events.get(event_id)
        if not event:
            raise KeyError(f"Unknown webhook event {event_id}")

        event.attempts += 1
        event.updated_at = datetime.now(timezone.utc).isoformat()

        body = json.dumps(event.payload, default=str)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AstrovoxAi-Webhook/1.0",
            "X-Webhook-Event": event.event_type,
            "X-Webhook-Id": event.event_id,
            "X-Webhook-Attempt": str(event.attempts),
        }
        sig = self._sign(event, body)
        if sig:
            headers["X-Webhook-Signature"] = f"sha256={sig}"

        try:
            response = await self._client.post(event.target_url, content=body, headers=headers)
            response.raise_for_status()
            event.status = DeliveryStatus.DELIVERED
            event.last_error = None
            logger.info(
                "Webhook delivered: %s -> %s (attempt %s)",
                event.event_type,
                event.target_url,
                event.attempts,
            )
        except Exception as exc:
            event.last_error = str(exc)
            logger.warning(
                "Webhook delivery failed: %s -> %s (attempt %s/%s): %s",
                event.event_type,
                event.target_url,
                event.attempts,
                event.max_attempts,
                exc,
            )
            if event.attempts >= event.max_attempts:
                event.status = DeliveryStatus.FAILED
                self._dlq.enqueue(
                    event.event_id,
                    {"event": event.event_type, "url": event.target_url, "payload": event.payload},
                    str(exc),
                    max_attempts=event.max_attempts,
                )
                logger.error("Webhook moved to DLQ: %s", event.event_id)

        return event

    async def retry_failed(self) -> List[WebhookEvent]:
        results = []
        for event in list(self._events.values()):
            if event.status in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING) and event.attempts < event.max_attempts:
                backoff = min(2.0 ** event.attempts, 60.0)
                await asyncio.sleep(backoff)
                result = await self.deliver(event.event_id)
                results.append(result)
        return results

    async def retry_dlq(self, dlq_id: str) -> bool:
        item = self._dlq.get(dlq_id)
        if not item:
            return False
        ok = self._dlq.retry(dlq_id)
        if not ok:
            logger.warning("DLQ item %s exhausted max retries", dlq_id)
            return False
        payload = item.payload
        event_id = payload.get("event_id", dlq_id)
        original = payload.get("original_task_id", dlq_id)
        logger.info("Retrying DLQ item %s (original %s)", dlq_id, original)
        event = WebhookEvent(
            event_id=event_id,
            event_type=payload.get("event", "unknown"),
            target_url=payload.get("url", ""),
            payload=payload.get("payload", {}),
            max_attempts=item.max_attempts,
            attempts=item.attempts,
        )
        self._events[event_id] = event
        await self.deliver(event_id)
        return True

    def get_event(self, event_id: str) -> Optional[WebhookEvent]:
        return self._events.get(event_id)

    def list_events(self, status: Optional[DeliveryStatus] = None) -> List[WebhookEvent]:
        events = list(self._events.values())
        if status:
            events = [e for e in events if e.status == status]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events

    def get_dlq_stats(self) -> Dict[str, Any]:
        return {
            "pending": len([d for d in self._dlq._queue.values() if d.status == DLQStatus.PENDING]),
            "dead": len([d for d in self._dlq._queue.values() if d.status == DLQStatus.DEAD]),
            "total": len(self._dlq._queue),
        }


_webhook_service: Optional["WebhookDeliveryService"] = None


def get_webhook_service() -> WebhookDeliveryService:
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookDeliveryService()
    return _webhook_service


# Backward compatibility alias
webhook_service = None  # initialized on first access via get_webhook_service()