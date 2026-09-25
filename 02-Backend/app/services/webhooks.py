"""Webhook delivery service with retries and backoff."""

from __future__ import annotations

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

logger = logging.getLogger("astravox.webhooks")


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


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


class WebhookDeliveryService:
    """Deliver webhook events with exponential backoff retries."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        self._events: Dict[str, WebhookEvent] = {}

    def register(self, event: WebhookEvent) -> None:
        self._events[event.event_id] = event

    async def deliver(self, event_id: str) -> WebhookEvent:
        event = self._events.get(event_id)
        if not event:
            raise KeyError(f"Unknown webhook event {event_id}")

        event.attempts += 1
        event.status = DeliveryStatus.RETRYING if event.attempts < event.max_attempts else DeliveryStatus.FAILED

        body = json.dumps(event.payload)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AstrovoxAi-Webhook/1.0",
            "X-Webhook-Event": event.event_type,
            "X-Webhook-Id": event.event_id,
            "X-Webhook-Attempt": str(event.attempts),
        }

        if event.secret:
            signature = hmac.new(event.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        try:
            response = await self._client.post(event.target_url, content=body, headers=headers)
            response.raise_for_status()
            event.status = DeliveryStatus.DELIVERED
            event.last_error = None
            logger.info("Webhook delivered: %s -> %s (attempt %s)", event.event_type, event.target_url, event.attempts)
        except Exception as exc:
            event.last_error = str(exc)
            logger.warning(
                "Webhook delivery failed: %s -> %s (attempt %s/%s): %s",
                event.event_type, event.target_url, event.attempts, event.max_attempts, exc,
            )

        return event

    async def retry_failed(self) -> List[WebhookEvent]:
        results = []
        for event in list(self._events.values()):
            if event.status in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING) and event.attempts < event.max_attempts:
                await asyncio.sleep(self._backoff(event.attempts))
                result = await self.deliver(event.event_id)
                results.append(result)
        return results

    def _backoff(self, attempt: int) -> float:
        return min(2.0 ** attempt, 60.0)

    def get_event(self, event_id: str) -> Optional[WebhookEvent]:
        return self._events.get(event_id)

    def list_events(self, status: Optional[DeliveryStatus] = None) -> List[WebhookEvent]:
        events = list(self._events.values())
        if status:
            events = [e for e in events if e.status == status]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events


webhook_service = WebhookDeliveryService()
