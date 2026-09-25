"""Push notifications."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class NotificationProvider(Enum):
    FIREBASE = "firebase"
    APNS = "apns"
    WEB_PUSH = "web_push"
    EMAIL = "email"
    SMS = "sms"


@dataclass
class PushNotification:
    notification_id: str
    user_id: str
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    provider: NotificationProvider = NotificationProvider.FIREBASE
    priority: str = "high"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PushNotificationManager:
    _notifications: Dict[str, PushNotification] = {}

    @classmethod
    async def send(cls, notification: PushNotification) -> bool:
        cls._notifications[notification.notification_id] = notification
        return True

    @classmethod
    async def send_bulk(cls, notifications: List[PushNotification]) -> List[bool]:
        return [await cls.send(n) for n in notifications]

    @classmethod
    def get_notification(cls, notification_id: str) -> Optional[PushNotification]:
        return cls._notifications.get(notification_id)

    @classmethod
    def get_user_notifications(cls, user_id: str) -> List[PushNotification]:
        return [n for n in cls._notifications.values() if n.user_id == user_id]
