"""Meeting management for enterprise collaboration."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MeetingRecord:
    meeting_id: str
    title: str
    participants: List[str]
    transcript: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MeetingManager:
    def __init__(self) -> None:
        self._meetings: Dict[str, MeetingRecord] = {}

    def schedule(self, title: str, participants: List[str]) -> MeetingRecord:
        meeting_id = uuid.uuid4().hex
        meeting = MeetingRecord(meeting_id=meeting_id, title=title, participants=participants)
        self._meetings[meeting_id] = meeting
        return meeting

    def get_meeting(self, meeting_id: str) -> Optional[MeetingRecord]:
        return self._meetings.get(meeting_id)


meeting_manager = MeetingManager()
