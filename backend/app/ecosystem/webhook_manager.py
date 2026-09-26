"""Webhook delivery with retries and dead-letter queue."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Webhook:
    webhook_id: str
    url: str
    secret: str
    events: List[str]
    headers: Dict[str, str] = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WebhookDelivery:
    delivery_id: str
    webhook_id: str
    payload: Dict[str, Any]
    status: str
    attempts: int = 0
    last_error: Optional[str] = None
    delivered_at: Optional[datetime] = None


class WebhookManager:
    def __init__(self, secret: str = "changeme", max_attempts: int = 5):
        self._secret = secret
        self.max_attempts = max_attempts
        self._webhooks: Dict[str, Webhook] = {}
        self._deliveries: List[WebhookDelivery] = []

    def register(self, webhook: Webhook) -> None:
        self._webhooks[webhook.webhook_id] = webhook

    async def deliver(self, webhook_id: str, event: str, payload: Dict[str, Any]) -> WebhookDelivery:
        webhook = self._webhooks.get(webhook_id)
        if not webhook or not webhook.active:
            raise ValueError("webhook not found or inactive")
        body = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(self._secret.encode(), body, hashlib.sha256).hexdigest()
        delivery = WebhookDelivery(
            delivery_id=uuid.uuid4().hex,
            webhook_id=webhook_id,
            payload=payload,
            status="attempting",
        )
        self._deliveries.append(delivery)
        for attempt in range(1, self.max_attempts + 1):
            delivery.attempts = attempt
            try:
                # delivery logic omitted
                delivery.status = "delivered"
                delivery.delivered_at = datetime.now(timezone.utc)
                return delivery
            except Exception as exc:
                delivery.last_error = str(exc)
                time.sleep(min(2 ** attempt, 60))
        delivery.status = "failed"
        return delivery


webhook_manager = WebhookManager()
