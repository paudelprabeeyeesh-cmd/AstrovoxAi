"""Real User Monitoring (RUM)."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RUMEvent:
    event_id: str
    user_id: str
    session_id: str
    event_type: str
    page_url: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class RUMManager:
    _events: List[RUMEvent] = []

    @classmethod
    def record_event(cls, user_id: str, session_id: str, event_type: str, page_url: str, metadata: Optional[Dict[str, Any]] = None) -> RUMEvent:
        event = RUMEvent(
            event_id=f"rum_{datetime.now(timezone.utc).timestamp()}",
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            page_url=page_url,
            metadata=metadata or {},
        )
        cls._events.append(event)
        return event

    @classmethod
    def get_page_views(cls, page_url: Optional[str] = None) -> List[RUMEvent]:
        if page_url:
            return [e for e in cls._events if e.page_url == page_url]
        return [e for e in cls._events if e.event_type == "pageview"]

    @classmethod
    def get_user_journey(cls, user_id: str) -> List[RUMEvent]:
        return [e for e in cls._events if e.user_id == user_id]
