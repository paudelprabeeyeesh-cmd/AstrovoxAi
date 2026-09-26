"""Google Workspace integration adapter."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GoogleWorkspaceAdapter:
    def __init__(self, credentials: Optional[dict] = None):
        self.credentials = credentials or {}

    def gmail_send(self, to: str, subject: str, body: str) -> dict:
        return {"message_id": "gmail-123", "to": to, "subject": subject, "status": "sent"}

    def drive_upload(self, file_path: str, mime_type: str) -> dict:
        return {"file_id": "drive-123", "name": file_path.split("/")[-1], "mime_type": mime_type}

    def calendar_list(self, calendar_id: str = "primary") -> list[dict]:
        return [
            {"id": "cal-1", "summary": "Team Sync", "start": "2026-09-27T10:00:00Z", "end": "2026-09-27T11:00:00Z"},
        ]


google_workspace = GoogleWorkspaceAdapter()
