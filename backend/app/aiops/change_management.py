"""Change management for production changes."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class ChangeStatus(Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ChangeRequest:
    request_id: str
    title: str
    description: str
    requester_id: str
    status: ChangeStatus = ChangeStatus.REQUESTED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChangeManager:
    def __init__(self) -> None:
        self._requests: Dict[str, ChangeRequest] = {}

    def create_request(self, request: ChangeRequest) -> ChangeRequest:
        request.request_id = request.request_id or uuid.uuid4().hex
        self._requests[request.request_id] = request
        return request

    def approve(self, request_id: str) -> Optional[ChangeRequest]:
        request = self._requests.get(request_id)
        if request:
            request.status = ChangeStatus.APPROVED
        return request


change_manager = ChangeManager()
