"""Enhanced webhook management with retry queue and delivery tracking."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.event_bus import event_bus, Event, EventPriority
from app.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class WebhookStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


class WebhookDeliveryStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"


@dataclass
class WebhookEndpoint:
    endpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    secret: str = ""
    events: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    active: bool = True
    created_at: float = field(default_factory=time.time)
    owner_id: str = ""


@dataclass
class WebhookDelivery:
    delivery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    endpoint_id: str = ""
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: WebhookStatus = WebhookStatus.PENDING
    delivery_status: Optional[WebhookDeliveryStatus] = None
    attempts: int = 0
    max_attempts: int = 5
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    delivered_at: Optional[float] = None


class WebhookManager:
    def __init__(self, default_max_attempts: int = 5, default_timeout: float = 10.0):
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._deliveries: Dict[str, WebhookDelivery] = {}
        self._dead_letters: List[WebhookDelivery] = []
        self._default_max_attempts = default_max_attempts
        self._default_timeout = default_timeout
        self._event_subscriptions: Dict[str, List[str]] = {}

    def register_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        self._endpoints[endpoint.endpoint_id] = endpoint
        for event in endpoint.events:
            self._event_subscriptions.setdefault(event, []).append(endpoint.endpoint_id)
        logger.info("Registered webhook endpoint %s -> %s", endpoint.endpoint_id, endpoint.url)
        return endpoint

    def unregister_endpoint(self, endpoint_id: str) -> bool:
        endpoint = self._endpoints.pop(endpoint_id, None)
        if not endpoint:
            return False
        for event in endpoint.events:
            subs = self._event_subscriptions.get(event, [])
            if endpoint_id in subs:
                subs.remove(endpoint_id)
        logger.info("Unregistered webhook endpoint %s", endpoint_id)
        return True

    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        return self._endpoints.get(endpoint_id)

    def list_endpoints(self, owner_id: Optional[str] = None) -> List[WebhookEndpoint]:
        return [
            ep for ep in self._endpoints.values()
            if owner_id is None or ep.owner_id == owner_id
        ]

    def trigger_event(self, event_type: str, payload: Dict[str, Any]) -> List[WebhookDelivery]:
        endpoint_ids = self._event_subscriptions.get(event_type, [])
        deliveries: List[WebhookDelivery] = []
        for eid in endpoint_ids:
            endpoint = self._endpoints.get(eid)
            if not endpoint or not endpoint.active:
                continue
            delivery = WebhookDelivery(
                endpoint_id=eid,
                event_type=event_type,
                payload=payload,
                max_attempts=self._default_max_attempts,
            )
            self._deliveries[delivery.delivery_id] = delivery
            deliveries.append(delivery)
            self._enqueue_delivery(delivery, endpoint)
        if deliveries:
            event_bus.publish(Event(
                event_type="webhook.triggered",
                payload={"event_type": event_type, "delivery_count": len(deliveries)},
                source="webhook_manager",
            ))
        return deliveries

    def _enqueue_delivery(self, delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> None:
        from app.message_queue import message_queue
        message_queue.enqueue(
            "webhook_deliveries",
            {
                "delivery_id": delivery.delivery_id,
                "endpoint_id": delivery.endpoint_id,
                "event_type": delivery.event_type,
                "payload": delivery.payload,
                "attempt": delivery.attempts,
            },
            priority=1,
        )

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0, jitter=True)
    def _deliver(self, delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> None:
        import httpx
        payload_bytes = json.dumps(delivery.payload, default=str).encode()
        signature = hmac.new(
            endpoint.secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Id": delivery.delivery_id,
            "X-Webhook-Signature-256": signature,
            "X-Webhook-Event": delivery.event_type,
            **endpoint.headers,
        }
        timeout = self._default_timeout
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint.url, content=payload_bytes, headers=headers)
            delivery.response_code = response.status_code
            delivery.response_body = response.text[:2000]
            if response.status_code < 300:
                delivery.delivery_status = WebhookDeliveryStatus.SUCCESS
                delivery.status = WebhookStatus.DELIVERED
                delivery.delivered_at = time.time()
                logger.info("Webhook delivered: %s -> %s (%d)", delivery.delivery_id, endpoint.url, response.status_code)
            else:
                delivery.delivery_status = WebhookDeliveryStatus.FAILURE
                delivery.error = f"HTTP {response.status_code}"
                delivery.attempts += 1
                if delivery.attempts >= delivery.max_attempts:
                    delivery.status = WebhookStatus.DEAD_LETTERED
                    self._dead_letters.append(delivery)
                    logger.error("Webhook dead-lettered: %s after %d attempts", delivery.delivery_id, delivery.attempts)
                else:
                    delivery.status = WebhookStatus.RETRYING
                    raise RuntimeError(f"Webhook delivery failed with HTTP {response.status_code}")
        except httpx.TimeoutException:
            delivery.delivery_status = WebhookDeliveryStatus.TIMEOUT
            delivery.error = "timeout"
            delivery.attempts += 1
            if delivery.attempts >= delivery.max_attempts:
                delivery.status = WebhookStatus.DEAD_LETTERED
                self._dead_letters.append(delivery)
            else:
                delivery.status = WebhookStatus.RETRYING
                raise

    def retry_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        delivery = self._deliveries.get(delivery_id)
        if not delivery or delivery.status not in (WebhookStatus.FAILED, WebhookStatus.DEAD_LETTERED):
            return None
        endpoint = self._endpoints.get(delivery.endpoint_id)
        if not endpoint:
            return None
        delivery.status = WebhookStatus.PENDING
        delivery.attempts = 0
        delivery.error = None
        self._enqueue_delivery(delivery, endpoint)
        logger.info("Re-enqueued webhook delivery %s", delivery_id)
        return delivery

    def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        return self._deliveries.get(delivery_id)

    def get_dead_letters(self, endpoint_id: Optional[str] = None) -> List[WebhookDelivery]:
        if endpoint_id:
            return [d for d in self._dead_letters if d.endpoint_id == endpoint_id]
        return list(self._dead_letters)

    def get_delivery_stats(self, endpoint_id: Optional[str] = None) -> Dict[str, Any]:
        deliveries = list(self._deliveries.values())
        if endpoint_id:
            deliveries = [d for d in deliveries if d.endpoint_id == endpoint_id]
        total = len(deliveries)
        delivered = sum(1 for d in deliveries if d.status == WebhookStatus.DELIVERED)
        failed = sum(1 for d in deliveries if d.status in (WebhookStatus.FAILED, WebhookStatus.DEAD_LETTERED))
        return {
            "total_deliveries": total,
            "delivered": delivered,
            "failed": failed,
            "dead_lettered": len(self._dead_letters),
            "success_rate": round(delivered / total, 4) if total else 0.0,
        }


webhook_manager = WebhookManager()
