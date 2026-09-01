"""Notifications & Activity system — unified notification delivery."""

import time
import uuid
from typing import Optional
from dataclasses import dataclass, field

from .models import ActivityEvent, Notification


class NotificationService:
    """Service for notifications and activity tracking."""

    def __init__(self):
        self._notifications: dict[str, list[Notification]] = {}  # user_id -> notifications
        self._activities: dict[str, list[ActivityEvent]] = {}  # org_id -> activities

    def notify(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        organization_id: str = "",
        workspace_id: str = "",
        data: Optional[dict] = None,
    ) -> Notification:
        """Create and store a notification."""
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            type=type,
            title=title,
            message=message,
            data=data or {},
        )

        if user_id not in self._notifications:
            self._notifications[user_id] = []
        self._notifications[user_id].insert(0, notification)

        # Keep only last 100 notifications per user
        self._notifications[user_id] = self._notifications[user_id][:100]

        return notification

    def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[Notification]:
        """Get notifications for a user."""
        notifs = self._notifications.get(user_id, [])
        if unread_only:
            notifs = [n for n in notifs if not n.is_read]
        return notifs[:limit]

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read."""
        notifs = self._notifications.get(user_id, [])
        for n in notifs:
            if n.id == notification_id:
                n.is_read = True
                return True
        return False

    def mark_all_read(self, user_id: str):
        """Mark all notifications as read."""
        notifs = self._notifications.get(user_id, [])
        for n in notifs:
            n.is_read = True

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        notifs = self._notifications.get(user_id, [])
        return sum(1 for n in notifs if not n.is_read)

    # ========================================================================
    # Activity Timeline
    # ========================================================================

    def log_activity(
        self,
        organization_id: str,
        user_id: str,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        workspace_id: str = "",
        metadata: Optional[dict] = None,
    ) -> ActivityEvent:
        """Log an activity event."""
        event = ActivityEvent(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
        )

        if organization_id not in self._activities:
            self._activities[organization_id] = []
        self._activities[organization_id].insert(0, event)

        # Keep only last 1000 activities per org
        self._activities[organization_id] = self._activities[organization_id][:1000]

        return event

    def get_activities(
        self,
        organization_id: str,
        workspace_id: str = "",
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get activity timeline."""
        activities = self._activities.get(organization_id, [])
        if workspace_id:
            activities = [a for a in activities if a.workspace_id == workspace_id]
        return activities[:limit]


# Global service instance
notification_service = NotificationService()
