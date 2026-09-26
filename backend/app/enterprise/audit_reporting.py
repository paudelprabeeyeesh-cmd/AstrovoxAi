"""Audit reporting — scheduled and ad-hoc compliance report generation."""

import csv
import io
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .audit_log import compliance_logger
from .compliance import compliance_generator

logger = logging.getLogger(__name__)


@dataclass
class AuditReport:
    report_id: str
    tenant_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    filters: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "generated"
    download_url: str = ""


class AuditReporter:
    def __init__(self):
        self._reports: Dict[str, AuditReport] = {}

    def generate(self, tenant_id: str, report_type: str = "audit", start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, filters: Optional[Dict[str, Any]] = None) -> AuditReport:
        report_id = str(uuid.uuid4())
        start = start_date or datetime.now(timezone.utc).replace(day=1)
        end = end_date or datetime.now(timezone.utc)
        report = AuditReport(
            report_id=report_id,
            tenant_id=tenant_id,
            report_type=report_type,
            period_start=start,
            period_end=end,
            filters=filters or {},
        )
        self._reports[report_id] = report
        logger.info("Generated audit report %s for tenant %s type %s", report_id, tenant_id, report_type)
        return report

    def get_report(self, report_id: str) -> Optional[AuditReport]:
        return self._reports.get(report_id)

    def export(self, report: AuditReport, fmt: str = "json") -> str:
        logs = compliance_logger.query(tenant_id=report.tenant_id)
        if fmt == "json":
            payload = {
                "report_id": report.report_id,
                "tenant_id": report.tenant_id,
                "report_type": report.report_type,
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "logs": logs,
                "summary": {"total_logs": len(logs)},
            }
            return json.dumps(payload, indent=2)
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["timestamp", "actor", "action", "resource", "tenant_id"])
            writer.writeheader()
            for entry in logs:
                writer.writerow({k: entry.get(k, "") for k in writer.fieldnames})
            return output.getvalue()
        raise ValueError(f"Unsupported format: {fmt}")

    def list_reports(self, tenant_id: str) -> List[dict]:
        return [
            {
                "report_id": r.report_id,
                "report_type": r.report_type,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "generated_at": r.generated_at.isoformat(),
                "status": r.status,
            }
            for r in self._reports.values()
            if r.tenant_id == tenant_id
        ]


audit_reporter = AuditReporter()
