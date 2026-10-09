import logging
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self._notifications: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def send_email(self, recipient: str, subject: str, body: str) -> dict:
        entry = {
            "type": "email",
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Email notification: %s", subject)
        return entry

    def send_in_app(self, user_id: str, message: str) -> dict:
        entry = {
            "type": "in_app",
            "user_id": user_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._notifications[user_id].append(entry)
        return entry

    def get_notifications(self, user_id: str, limit: int = 50) -> List[dict]:
        with self._lock:
            items = list(self._notifications.get(user_id, deque()))[-limit:]
        return items


notification_service = NotificationService()
