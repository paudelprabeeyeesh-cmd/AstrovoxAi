"""Omnipresent Notification System - Notifications across all realities."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class OmnipresentNotification:
    notification_id: str
    user_id: str
    title: str
    body: str
    channels: List[str] = field(default_factory=list)
    reality_layers: List[int] = field(default_factory=lambda: [0])
    priority: int = 0
    delivered: bool = False
    read: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class OmnipresentNotificationSystem:
    """Delivers notifications everywhere simultaneously across all channels."""

    DEFAULT_CHANNELS = ["in_app", "email", "sms", "push", "websocket", "reality"]
    PRIORITY_LEVELS = {"low": 0, "normal": 1, "high": 2, "critical": 3, "transcendent": 4}

    def __init__(self):
        self._notifications: Dict[str, OmnipresentNotification] = {}
        self._user_inbox: Dict[str, List[str]] = {}
        self._channel_registry: Dict[str, Dict[str, Any]] = {}
        self._delivery_log: List[Dict[str, Any]] = []
        for ch in self.DEFAULT_CHANNELS:
            self._channel_registry[ch] = {"active": True, "delivered": 0, "failed": 0}

    def send(self, user_id: str, title: str, body: str, channels: List[str] = None, reality_layers: List[int] = None, priority: str = "normal", metadata: Dict[str, Any] = None) -> OmnipresentNotification:
        notification_id = str(uuid.uuid4())
        notification = OmnipresentNotification(
            notification_id=notification_id,
            user_id=user_id,
            title=title,
            body=body,
            channels=channels or self.DEFAULT_CHANNELS,
            reality_layers=reality_layers or [0],
            priority=self.PRIORITY_LEVELS.get(priority, 1),
            metadata=metadata or {},
        )
        self._notifications[notification_id] = notification
        self._user_inbox.setdefault(user_id, []).append(notification_id)
        delivery = {
            "notification_id": notification_id,
            "user_id": user_id,
            "channels": notification.channels,
            "delivered": True,
            "timestamp": time.time(),
        }
        for ch in notification.channels:
            if ch in self._channel_registry:
                self._channel_registry[ch]["delivered"] += 1
        self._delivery_log.append(delivery)
        notification.delivered = True
        return notification

    def broadcast(self, title: str, body: str, channels: List[str] = None, priority: str = "normal") -> List[OmnipresentNotification]:
        notifications = []
        for user_id in list(self._user_inbox.keys()):
            notifications.append(self.send(user_id, title, body, channels, priority=priority))
        return notifications

    def mark_read(self, notification_id: str) -> bool:
        notification = self._notifications.get(notification_id)
        if notification:
            notification.read = True
            return True
        return False

    def get_inbox(self, user_id: str, unread_only: bool = False) -> List[OmnipresentNotification]:
        notification_ids = self._user_inbox.get(user_id, [])
        notifications = [self._notifications[nid] for nid in notification_ids if nid in self._notifications]
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        notifications.sort(key=lambda n: n.timestamp, reverse=True)
        return notifications

    def get_channel_stats(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._channel_registry)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "notifications": len(self._notifications),
            "users": len(self._user_inbox),
            "deliveries": len(self._delivery_log),
            "channels": len(self._channel_registry),
        }
