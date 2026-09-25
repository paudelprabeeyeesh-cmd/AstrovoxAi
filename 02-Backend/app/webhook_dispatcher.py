"""Webhook dispatcher."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import aiohttp
import asyncio


@dataclass
class Webhook:
    webhook_id: str
    url: str
    secret: Optional[str] = None
    events: List[str] = field(default_factory=list)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    failure_count: int = 0


class WebhookDispatcher:
    _webhooks: Dict[str, Webhook] = {}

    @classmethod
    def register(cls, webhook: Webhook) -> None:
        cls._webhooks[webhook.webhook_id] = webhook

    @classmethod
    async def dispatch(cls, webhook_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        webhook = cls._webhooks.get(webhook_id)
        if not webhook or not webhook.active:
            return
        if webhook.events and event_type not in webhook.events:
            return
        headers = {"Content-Type": "application/json"}
        if webhook.secret:
            import hmac, hashlib
            signature = hmac.new(webhook.secret.encode(), str(payload).encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook.url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status < 400:
                        webhook.last_triggered = datetime.now(timezone.utc)
                        webhook.failure_count = 0
                    else:
                        webhook.failure_count += 1
        except Exception:
            webhook.failure_count += 1

    @classmethod
    async def dispatch_to_all(cls, event_type: str, payload: Dict[str, Any]) -> None:
        for webhook in cls._webhooks.values():
            await cls.dispatch(webhook.webhook_id, event_type, payload)
