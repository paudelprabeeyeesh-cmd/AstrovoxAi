"""Report engine for automated reporting."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduledReport:
    report_id: str
    name: str
    query: str
    schedule: str
    recipients: List[str] = field(default_factory=list)
    format: str = "pdf"
    last_run: Optional[datetime] = None


class ReportEngine:
    def __init__(self) -> None:
        self._reports: Dict[str, ScheduledReport] = {}

    def create_report(self, report: ScheduledReport) -> ScheduledReport:
        report.report_id = report.report_id or uuid.uuid4().hex
        self._reports[report.report_id] = report
        return report

    async def generate(self, report_id: str) -> Dict[str, Any]:
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Unknown report: {report_id}")
        report.last_run = datetime.now(timezone.utc)
        return {"report_id": report_id, "status": "generated", "format": report.format}


report_engine = ReportEngine()
