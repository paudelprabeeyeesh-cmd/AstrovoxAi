"""Webhook registration, delivery, and retry logic."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    EVALUATION_COMPLETED = "evaluation.completed"
    SAFETY_ALERT = "safety.alert"
    AGENT_STATE_CHANGED = "agent.state_changed"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    QUOTA_EXCEEDED = "quota.exceeded"


@dataclass
class Webhook:
    id: str
    org_id: str
    url: str
    events: list[str]
    secret: Optional[str] = None
    active: bool = True
    headers: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WebhookDelivery:
    id: str
    webhook_id: str
    event_type: str
    payload: dict
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    attempts: int = 0
    last_error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WebhookManager:
    def __init__(self):
        self._webhooks: dict[str, Webhook] = {}

    def register(self, org_id: str, url: str, events: list[str], secret: Optional[str] = None, headers: Optional[dict] = None) -> Webhook:
        webhook_id = str(uuid.uuid4())
        webhook = Webhook(
            id=webhook_id,
            org_id=org_id,
            url=url,
            events=events,
            secret=secret,
            headers=headers or {},
        )
        self._webhooks[webhook_id] = webhook
        self._persist(webhook)
        return webhook

    def _persist(self, webhook: Webhook):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO webhooks (id, org_id, url, events, secret, active, headers, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    webhook.id,
                    webhook.org_id,
                    webhook.url,
                    json.dumps(webhook.events),
                    webhook.secret,
                    1 if webhook.active else 0,
                    json.dumps(webhook.headers),
                    json.dumps(webhook.metadata),
                    webhook.created_at,
                ),
            )
            conn.commit()

    def list_webhooks(self, org_id: str) -> list[Webhook]:
        return [w for w in self._webhooks.values() if w.org_id == org_id]

    def deliver(self, event_type: str, payload: dict, org_id: str) -> list[WebhookDelivery]:
        deliveries = []
        for webhook in self.list_webhooks(org_id):
            if not webhook.active or event_type not in webhook.events:
                continue
            delivery = self._send(webhook, event_type, payload)
            deliveries.append(delivery)
        return deliveries

    def _send(self, webhook: Webhook, event_type: str, payload: dict) -> WebhookDelivery:
        import requests

        delivery_id = str(uuid.uuid4())
        delivery = WebhookDelivery(id=delivery_id, webhook_id=webhook.id, event_type=event_type, payload=payload)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-ID": webhook.id,
            **(webhook.headers or {}),
        }
        if webhook.secret:
            import hmac, hashlib
            signature = hmac.new(webhook.secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        try:
            response = requests.post(webhook.url, json=payload, headers=headers, timeout=10)
            delivery.status_code = response.status_code
            delivery.response_body = response.text[:500]
            delivery.attempts = 1
            if response.status_code >= 400:
                delivery.last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            delivery.last_error = str(exc)
            delivery.attempts = 1
        self._persist_delivery(delivery)
        return delivery

    def _persist_delivery(self, delivery: WebhookDelivery):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO webhook_deliveries (id, webhook_id, event_type, payload, status_code, response_body, attempts, last_error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    delivery.id,
                    delivery.webhook_id,
                    delivery.event_type,
                    json.dumps(delivery.payload),
                    delivery.status_code,
                    delivery.response_body,
                    delivery.attempts,
                    delivery.last_error,
                    delivery.created_at,
                ),
            )
            conn.commit()

    def retry_failed(self, webhook_id: str) -> bool:
        # Placeholder for retry logic
        return True


webhook_manager = WebhookManager()
