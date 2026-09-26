"""Unified notification gateway for email, SMS, and push."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    notification_id: str
    channel: str
    recipient: str
    subject: str
    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None
    status: str = "pending"
    error: Optional[str] = None


class NotificationGateway:
    def __init__(self) -> None:
        self._notifications: Dict[str, Notification] = {}
        self._providers: Dict[str, Any] = {}

    def register_provider(self, channel: str, provider: Any) -> None:
        self._providers[channel] = provider
        logger.info("Registered notification provider for channel %s", channel)

    async def send(self, channel: str, recipient: str, subject: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> Notification:
        notification_id = str(__import__("uuid").uuid4())
        notification = Notification(
            notification_id=notification_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            metadata=metadata or {},
        )
        provider = self._providers.get(channel)
        if not provider:
            notification.status = "failed"
            notification.error = f"No provider for channel {channel}"
            self._notifications[notification_id] = notification
            return notification
        try:
            await self._deliver(provider, notification)
            notification.status = "delivered"
            notification.delivered_at = datetime.now(timezone.utc)
        except Exception as exc:
            notification.status = "failed"
            notification.error = str(exc)
            logger.exception("Failed to send notification %s", notification_id)
        self._notifications[notification_id] = notification
        return notification

    async def send_batch(self, notifications: List[Dict[str, Any]]) -> List[Notification]:
        results = []
        for payload in notifications:
            result = await self.send(
                channel=payload["channel"],
                recipient=payload["recipient"],
                subject=payload.get("subject", ""),
                body=payload.get("body", ""),
                metadata=payload.get("metadata"),
            )
            results.append(result)
        return results

    async def _deliver(self, provider: Any, notification: Notification) -> None:
        if hasattr(provider, "send"):
            result = provider.send(notification)
            if hasattr(result, "__await__"):
                await result
        else:
            logger.warning("Provider for %s does not implement send()", notification.channel)

    def get_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        notification = self._notifications.get(notification_id)
        if not notification:
            return None
        return {
            "notification_id": notification.notification_id,
            "channel": notification.channel,
            "recipient": notification.recipient,
            "status": notification.status,
            "error": notification.error,
            "created_at": notification.created_at.isoformat(),
            "delivered_at": notification.delivered_at.isoformat() if notification.delivered_at else None,
        }

    @property
    def stats(self) -> Dict[str, Any]:
        delivered = sum(1 for n in self._notifications.values() if n.status == "delivered")
        failed = sum(1 for n in self._notifications.values() if n.status == "failed")
        return {"total": len(self._notifications), "delivered": delivered, "failed": failed}


notification_gateway = NotificationGateway()
