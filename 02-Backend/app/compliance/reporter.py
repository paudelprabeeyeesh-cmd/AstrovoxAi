
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from .collector import EvidenceCollector


class ComplianceReporter:
    def __init__(self):
        self.collector = EvidenceCollector()

    def generate_report(self, org_id: str, framework: str, start_date: datetime, end_date: datetime) -> dict:
        evidence = self.collector.collect_all(org_id, start_date, end_date)
        report = {
            "report_id": str(uuid.uuid4()),
            "org_id": org_id,
            "framework": framework,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evidence": evidence,
            "summary": self._summarize(evidence),
        }
        return report

    def _summarize(self, evidence: Dict[str, List[dict]]) -> dict:
        return {
            "audit_logs_count": len(evidence.get("audit_logs", [])),
            "access_logs_count": len(evidence.get("access_logs", [])),
            "metrics_count": len(evidence.get("metrics", [])),
            "config_count": len(evidence.get("configuration", [])),
        }

    def export_report(self, report: dict, format: str = "json") -> str:
        if format == "json":
            return json.dumps(report, default=str, indent=2)
        if format == "csv":
            lines = ["field,value"]
            for key, value in report.items():
                if isinstance(value, (str, int, float)):
                    lines.append(f"{key},{value}")
            return "\n".join(lines)
        raise ValueError(f"Unsupported format: {format}")
