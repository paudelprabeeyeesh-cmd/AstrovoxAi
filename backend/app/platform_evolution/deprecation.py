"""Deprecation management for APIs and features."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeprecationNotice:
    notice_id: str
    feature: str
    deprecated_in_version: str
    removal_version: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DeprecationManager:
    def __init__(self) -> None:
        self._notices: Dict[str, DeprecationNotice] = {}

    def deprecate(self, feature: str, deprecated_in_version: str, removal_version: str, message: str) -> DeprecationNotice:
        notice_id = uuid.uuid4().hex
        notice = DeprecationNotice(
            notice_id=notice_id,
            feature=feature,
            deprecated_in_version=deprecated_in_version,
            removal_version=removal_version,
            message=message,
        )
        self._notices[notice_id] = notice
        return notice

    def list_notices(self) -> List[DeprecationNotice]:
        return list(self._notices.values())


deprecation_manager = DeprecationManager()
