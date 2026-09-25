
from datetime import datetime, timezone
from .reporter import ComplianceReporter
from .collector import EvidenceCollector


class SOC2Evidence:
    def __init__(self):
        self.reporter = ComplianceReporter()
        self.collector = EvidenceCollector()

    def collect_trust_services_criteria(self, org_id: str, start_date: datetime, end_date: datetime) -> dict:
        evidence = self.collector.collect_all(org_id, start_date, end_date)
        return {
            "cc6_1_logical_access": self._check_logical_access(evidence),
            "cc6_6_security_events": self._check_security_events(evidence),
            "cc7_2_system_monitoring": self._check_system_monitoring(evidence),
            "cc7_4_incident_response": self._check_incident_response(evidence),
            "cc8_1_change_management": self._check_change_management(evidence),
        }

    def _check_logical_access(self, evidence: dict) -> dict:
        access_logs = evidence.get("access_logs", [])
        return {
            "status": "pass" if len(access_logs) > 0 else "needs_review",
            "total_events": len(access_logs),
            "unique_users": len(set(r.get("user_id") for r in access_logs if r.get("user_id"))),
        }

    def _check_security_events(self, evidence: dict) -> dict:
        audit_logs = evidence.get("audit_logs", [])
        security_events = [r for r in audit_logs if r.get("action") in ("login_failed", "permission_denied", "suspicious_activity")]
        return {
            "status": "pass" if len(security_events) == 0 else "needs_review",
            "total_events": len(security_events),
        }

    def _check_system_monitoring(self, evidence: dict) -> dict:
        metrics = evidence.get("metrics", [])
        return {
            "status": "pass" if len(metrics) > 0 else "needs_review",
            "total_metrics": len(metrics),
        }

    def _check_incident_response(self, evidence: dict) -> dict:
        audit_logs = evidence.get("audit_logs", [])
        incidents = [r for r in audit_logs if r.get("action") in ("incident_created", "incident_resolved")]
        return {
            "status": "pass" if len(incidents) > 0 else "needs_review",
            "total_incidents": len(incidents),
        }

    def _check_change_management(self, evidence: dict) -> dict:
        audit_logs = evidence.get("audit_logs", [])
        changes = [r for r in audit_logs if r.get("action") in ("config_change", "deployment")]
        return {
            "status": "pass",
            "total_changes": len(changes),
        }

    def generate_soc2_report(self, org_id: str, start_date: datetime, end_date: datetime) -> dict:
        criteria = self.collect_trust_services_criteria(org_id, start_date, end_date)
        report = self.reporter.generate_report(org_id, "SOC2", start_date, end_date)
        report["trust_services_criteria"] = criteria
        return report
