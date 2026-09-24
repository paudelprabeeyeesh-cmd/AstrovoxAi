"""
Notification system with channels, alerts, and subscriptions.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Notification:
    channel: str
    subject: str
    body: str
    severity: str = "info"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


ChannelHandler = Callable[[Notification], None]


class NotificationSystem:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._channels: Dict[str, List[ChannelHandler]] = {}
        self._subscriptions: Dict[str, List[str]] = {}

    def register_channel(self, name: str, handler: ChannelHandler) -> None:
        with self._lock:
            self._channels.setdefault(name, []).append(handler)

    def subscribe(self, topic: str, channel: str) -> None:
        with self._lock:
            self._subscriptions.setdefault(topic, set()).add(channel)

    def send(self, notification: Notification) -> None:
        with self._lock:
            handlers = list(self._channels.get(notification.channel, []))
            topics = list(self._subscriptions.get(notification.channel, set()))
        for handler in handlers:
            try:
                handler(notification)
            except Exception:
                continue
        for topic in topics:
            for target_handler in self._channels.get(topic, []):
                if target_handler not in handlers:
                    try:
                        target_handler(notification)
                    except Exception:
                        continue

    def list_channels(self) -> List[str]:
        with self._lock:
            return list(self._channels.keys())
