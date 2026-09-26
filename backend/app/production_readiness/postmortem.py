"""Postmortem management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PostmortemReport:
    report_id: str
    incident_id: str
    summary: str
    timeline: List[str]
    action_items: List[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PostmortemManager:
    def __init__(self) -> None:
        self._reports: Dict[str, PostmortemReport] = {}

    def create_report(self, report: PostmortemReport) -> PostmortemReport:
        report.report_id = report.report_id or uuid.uuid4().hex
        self._reports[report.report_id] = report
        return report

    def get_report(self, report_id: str) -> Optional[PostmortemReport]:
        return self._reports.get(report_id)


postmortem_manager = PostmortemManager()
