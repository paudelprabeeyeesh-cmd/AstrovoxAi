"""Compliance report generator."""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .audit import audit_exporter
from .tenancy import tenant_manager

logger = logging.getLogger(__name__)


@dataclass
class ComplianceReport:
    report_id: str
    tenant_id: str
    framework: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: Dict[str, List[dict]] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    status: str = "generated"


class ComplianceReportGenerator:
    def __init__(self):
        self._reports: Dict[str, ComplianceReport] = {}

    def generate(self, tenant_id: str, framework: str, start_date: datetime, end_date: datetime) -> ComplianceReport:
        report_id = str(uuid.uuid4())
        evidence = self._collect_evidence(tenant_id, start_date, end_date)
        summary = self._summarize(evidence)
        report = ComplianceReport(
            report_id=report_id,
            tenant_id=tenant_id,
            framework=framework,
            period_start=start_date,
            period_end=end_date,
            evidence=evidence,
            summary=summary,
        )
        self._reports[report_id] = report
        logger.info("Generated compliance report %s for tenant %s framework %s", report_id, tenant_id, framework)
        return report

    def _collect_evidence(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, List[dict]]:
        audit_result = audit_exporter.export(
            requester_id=tenant_id,
            format="json",
            filters={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        logs = audit_result.get("logs", [])
        return {
            "audit_logs": logs,
            "access_logs": [l for l in logs if l.get("action") in ("login", "logout", "api_call")],
            "tamper_evidence": audit_result.get("tamper_evidence", {}),
            "metadata": {
                "tenant_id": tenant_id,
                "framework": "",
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
            },
        }

    def _summarize(self, evidence: Dict[str, List[dict]]) -> Dict[str, Any]:
        return {
            "audit_logs_count": len(evidence.get("audit_logs", [])),
            "access_logs_count": len(evidence.get("access_logs", [])),
            "tamper_detected": evidence.get("tamper_evidence", {}).get("tampered", False),
        }

    def export_report(self, report: ComplianceReport, fmt: str = "json") -> str:
        data = {
            "report_id": report.report_id,
            "tenant_id": report.tenant_id,
            "framework": report.framework,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "generated_at": report.generated_at.isoformat(),
            "status": report.status,
            "summary": report.summary,
            "evidence": report.evidence,
        }
        if fmt == "json":
            return json.dumps(data, default=str, indent=2)
        if fmt == "csv":
            lines = ["field,value"]
            for key, value in data.items():
                if isinstance(value, (str, int, float)):
                    lines.append(f"{key},{value}")
            return "\n".join(lines)
        raise ValueError(f"Unsupported format: {fmt}")

    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        return self._reports.get(report_id)


compliance_generator = ComplianceReportGenerator()
