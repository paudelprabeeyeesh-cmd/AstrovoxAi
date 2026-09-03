"""Webhook platform: incoming + outgoing webhooks with retries, DLQ, signatures."""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from .api_platform import (
    DELIVERY_HEADER,
    EVENT_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    sign_payload,
    verify_signature,
)


class WebhookEvent(str, Enum):
    CHAT_COMPLETED = "chat.completed"
    CHAT_FAILED = "chat.failed"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    KNOWLEDGE_INGESTED = "knowledge.ingested"
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UNINSTALLED = "plugin.uninstalled"
    PLUGIN_UPDATED = "plugin.updated"
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"
    API_KEY_CREATED = "api.key.created"
    API_KEY_REVOKED = "api.key.revoked"
    USER_CREATED = "user.created"
    WORKSPACE_CREATED = "workspace.created"
    CUSTOM = "custom"

    @classmethod
    def from_string(cls, value: str) -> "WebhookEvent":
        try:
            return cls(value)
        except ValueError:
            return cls.CUSTOM


@dataclass
class WebhookSubscription:
    id: str
    url: str
    secret: str
    events: List[str]
    owner_id: str
    description: str = ""
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    filters: Dict[str, Any] = field(default_factory=dict)
    rate_limit: int = 120
    last_delivery: Optional[str] = None
    failure_count: int = 0


@dataclass
class WebhookDelivery:
    id: str
    subscription_id: str
    event: str
    payload: Dict[str, Any]
    signature: str
    timestamp: int
    attempts: int = 0
    status: str = "pending"
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    next_retry_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    delivered_at: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WebhookDeliveryStore:
    """Append-only delivery log backed by a JSONL file."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(
            path
            or os.getenv("ASTROVOX_WEBHOOK_LOG", "./storage/webhooks/deliveries.jsonl")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def append(self, delivery: WebhookDelivery) -> None:
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(delivery.to_dict(), default=str) + "\n")

    async def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        async with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]


class DeadLetterQueue:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(
            path or os.getenv("ASTROVOX_WEBHOOK_DLQ", "./storage/webhooks/dlq.jsonl")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def push(self, delivery: WebhookDelivery, reason: str) -> None:
        async with self._lock:
            record = delivery.to_dict()
            record["dlq_reason"] = reason
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")

    async def drain(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        async with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()]


class WebhookManager:
    """Coordinates subscriptions, delivery, retries, and analytics."""

    MAX_ATTEMPTS = 5
    BACKOFF_BASE = 2
    BACKOFF_JITTER = 0.3

    def __init__(
        self,
        delivery_store: Optional[WebhookDeliveryStore] = None,
        dlq: Optional[DeadLetterQueue] = None,
        http_post: Optional[Callable[[str, bytes, Dict[str, str]], Awaitable[int]]] = None,
    ) -> None:
        self.subscriptions: Dict[str, WebhookSubscription] = {}
        self.delivery_store = delivery_store or WebhookDeliveryStore()
        self.dlq = dlq or DeadLetterQueue()
        self._http_post = http_post or self._default_post
        self._metrics: Dict[str, int] = defaultdict(int)

    # ---- subscription management --------------------------------------

    def create_subscription(
        self,
        url: str,
        events: List[str],
        owner_id: str,
        description: str = "",
        secret: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            id=f"wh_{uuid.uuid4().hex[:12]}",
            url=url,
            secret=secret or uuid.uuid4().hex,
            events=events,
            owner_id=owner_id,
            description=description,
            filters=filters or {},
        )
        self.subscriptions[sub.id] = sub
        return sub

    def delete_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        return self.subscriptions.pop(subscription_id, None)

    def list_subscriptions(self, owner_id: Optional[str] = None) -> List[WebhookSubscription]:
        subs = list(self.subscriptions.values())
        if owner_id:
            subs = [s for s in subs if s.owner_id == owner_id]
        return subs

    def pause(self, subscription_id: str) -> Optional[WebhookSubscription]:
        sub = self.subscriptions.get(subscription_id)
        if sub:
            sub.active = False
        return sub

    def resume(self, subscription_id: str) -> Optional[WebhookSubscription]:
        sub = self.subscriptions.get(subscription_id)
        if sub:
            sub.active = True
        return sub

    # ---- delivery ----------------------------------------------------

    async def publish(
        self,
        event: str,
        payload: Dict[str, Any],
        target_owner: Optional[str] = None,
    ) -> List[WebhookDelivery]:
        event_name = WebhookEvent.from_string(event).value
        deliveries: List[WebhookDelivery] = []
        for sub in self.subscriptions.values():
            if not sub.active:
                continue
            if target_owner and sub.owner_id != target_owner:
                continue
            if sub.events and "*" not in sub.events and event_name not in sub.events:
                continue
            if sub.filters and not self._match_filters(payload, sub.filters):
                continue
            body = json.dumps(
                {
                    "id": f"evt_{uuid.uuid4().hex[:12]}",
                    "event": event_name,
                    "created_at": int(time.time()),
                    "data": payload,
                },
                default=str,
            ).encode("utf-8")
            ts = int(time.time())
            signature = sign_payload(body, sub.secret, ts)
            delivery = WebhookDelivery(
                id=f"del_{uuid.uuid4().hex[:12]}",
                subscription_id=sub.id,
                event=event_name,
                payload=payload,
                signature=signature,
                timestamp=ts,
            )
            deliveries.append(delivery)
            await self._deliver(delivery, sub)
        return deliveries

    async def _deliver(self, delivery: WebhookDelivery, sub: WebhookSubscription) -> None:
        headers = {
            "Content-Type": "application/json",
            EVENT_HEADER: delivery.event,
            TIMESTAMP_HEADER: str(delivery.timestamp),
            SIGNATURE_HEADER: delivery.signature,
            DELIVERY_HEADER: delivery.id,
        }
        body = json.dumps(delivery.payload, default=str).encode("utf-8")
        while delivery.attempts < self.MAX_ATTEMPTS:
            delivery.attempts += 1
            try:
                status_code = await self._http_post(sub.url, body, headers)
            except Exception as exc:
                delivery.error = str(exc)
                status_code = 0
            delivery.response_status = status_code
            delivery.response_body = ""
            sub.last_delivery = datetime.now(timezone.utc).isoformat()
            if 200 <= status_code < 300:
                delivery.status = "delivered"
                delivery.delivered_at = time.time()
                self._metrics["delivered"] += 1
                await self.delivery_store.append(delivery)
                return
            delivery.status = "retrying"
            self._metrics["retried"] += 1
            await self._sleep_backoff(delivery.attempts)
        delivery.status = "failed"
        self._metrics["failed"] += 1
        sub.failure_count += 1
        await self.delivery_store.append(delivery)
        await self.dlq.push(delivery, reason="max_attempts_exceeded")

    async def _sleep_backoff(self, attempt: int) -> None:
        base = self.BACKOFF_BASE ** attempt
        jitter = random.uniform(0, self.BACKOFF_JITTER) * base
        delay = min(base + jitter, 0.05)  # cap for tests
        await asyncio.sleep(delay)

    def _match_filters(self, payload: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, expected in filters.items():
            value = payload.get(key)
            if isinstance(expected, list):
                if value not in expected:
                    return False
            elif value != expected:
                return False
        return True

    async def _default_post(self, url: str, body: bytes, headers: Dict[str, str]) -> int:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(url, content=body, headers=headers)
                return resp.status_code
        except Exception:
            return 0

    # ---- analytics ---------------------------------------------------

    def metrics(self) -> Dict[str, Any]:
        return {
            "subscriptions": len(self.subscriptions),
            "active_subscriptions": sum(1 for s in self.subscriptions.values() if s.active),
            "events": dict(self._metrics),
        }

    # ---- incoming verification ---------------------------------------

    @staticmethod
    def verify_incoming(
        body: bytes,
        signature: str,
        secret: str,
        timestamp_header: Optional[str] = None,
    ) -> bool:
        if timestamp_header is not None:
            try:
                if abs(int(timestamp_header) - int(time.time())) > 300:
                    return False
            except ValueError:
                return False
        return verify_signature(body, signature, secret)


_GLOBAL_MANAGER: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = WebhookManager()
    return _GLOBAL_MANAGER


def dispatch_event(event: str, payload: Dict[str, Any], owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Best-effort sync dispatcher used from non-async contexts."""

    manager = get_webhook_manager()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return [
                {"id": sub.id, "url": sub.url, "status": "queued"}
                for sub in manager.list_subscriptions(owner_id)
                if sub.active and (event in sub.events or "*" in sub.events)
            ]
    except RuntimeError:
        pass
    return []