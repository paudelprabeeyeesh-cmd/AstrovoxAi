import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MeetingPlatform(Enum):
    GOOGLE_CALENDAR = "google_calendar"
    OUTLOOK = "outlook"
    ZOOM = "zoom"
    TEAMS = "teams"


@dataclass
class MeetingEvent:
    event_id: str
    title: str
    description: str
    start_time: str
    end_time: str
    attendees: List[str] = field(default_factory=list)
    location: str = ""
    platform: MeetingPlatform = MeetingPlatform.GOOGLE_CALENDAR
    meeting_url: Optional[str] = None
    transcript_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    synced_count: int
    failed_count: int
    errors: List[str] = field(default_factory=list)


class CalendarMeetingSyncAdapter:
    def __init__(self, api_client):
        self.api_client = api_client
        self._meetings: Dict[str, MeetingEvent] = {}

    def register_meeting(self, meeting: MeetingEvent):
        self._meetings[meeting.event_id] = meeting
        logger.info(f"Registered meeting {meeting.event_id} on {meeting.platform.value}")

    def sync_to_calendar(self, conversation_id: str, platform: MeetingPlatform = MeetingPlatform.GOOGLE_CALENDAR) -> MeetingEvent:
        conversation = self.api_client.get_conversation(conversation_id)
        event_id = f"meeting-{conversation_id}"
        now = datetime.utcnow().isoformat()
        meeting = MeetingEvent(
            event_id=event_id,
            title=f"Astrovox: {conversation.title}",
            description="\n".join([f"{m.role}: {m.content}" for m in conversation.messages]),
            start_time=now,
            end_time=(datetime.utcnow() + timedelta(hours=1)).isoformat(),
            platform=platform
        )
        self._meetings[event_id] = meeting
        logger.info(f"Synced conversation {conversation_id} to {platform.value} meeting {event_id}")
        return meeting

    def sync_from_calendar(self, event_id: str) -> SyncResult:
        meeting = self._meetings.get(event_id)
        if not meeting:
            return SyncResult(synced_count=0, failed_count=1, errors=[f"Meeting {event_id} not found"])
        try:
            conv = self.api_client.create_conversation(title=meeting.title)
            for msg in meeting.metadata.get("messages", []):
                self.api_client.send_message(conv.id, msg.get("content", ""), msg.get("role", "user"))
            logger.info(f"Synced meeting {event_id} to conversation {conv.id}")
            return SyncResult(synced_count=1, failed_count=0)
        except Exception as e:
            logger.error(f"Failed to sync meeting {event_id}: {e}")
            return SyncResult(synced_count=0, failed_count=1, errors=[str(e)])

    def sync_recurring(self, event_ids: List[str]) -> Dict[str, SyncResult]:
        results = {}
        for event_id in event_ids:
            results[event_id] = self.sync_from_calendar(event_id)
        return results

    def get_meeting(self, event_id: str) -> Optional[MeetingEvent]:
        return self._meetings.get(event_id)

    def list_synced_meetings(self) -> List[MeetingEvent]:
        return list(self._meetings.values())

    def update_meeting_metadata(self, event_id: str, metadata: Dict[str, Any]):
        meeting = self._meetings.get(event_id)
        if not meeting:
            raise ValueError(f"Meeting {event_id} not found")
        meeting.metadata.update(metadata)
        logger.info(f"Updated metadata for meeting {event_id}")

    def delete_meeting(self, event_id: str) -> bool:
        if event_id in self._meetings:
            del self._meetings[event_id]
            logger.info(f"Deleted meeting {event_id}")
            return True
        return False
