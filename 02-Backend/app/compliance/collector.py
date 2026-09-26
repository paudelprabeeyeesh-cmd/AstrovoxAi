
from typing import List, Dict
from datetime import datetime
from app.repositories.database.client import get_db


class EvidenceCollector:
    def __init__(self):
        self.evidence_types = {
            "audit_logs": self._collect_audit_logs,
            "access_logs": self._collect_access_logs,
            "metrics": self._collect_metrics,
            "configuration": self._collect_configuration,
        }

    def collect(self, evidence_type: str, org_id: str, start_date: datetime, end_date: datetime) -> List[dict]:
        collector = self.evidence_types.get(evidence_type)
        if not collector:
            raise ValueError(f"Unknown evidence type: {evidence_type}")
        return collector(org_id, start_date, end_date)

    def _collect_audit_logs(self, org_id: str, start_date: datetime, end_date: datetime) -> List[dict]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT al.id, al.user_id, al.action, al.resource, al.details, al.created_at, u.email
                FROM audit_logs al
                LEFT JOIN users u ON u.id = al.user_id
                LEFT JOIN organization_members om ON om.user_id = al.user_id
                WHERE om.org_id = ? AND al.created_at BETWEEN ? AND ?
                ORDER BY al.created_at DESC
                """,
                (org_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
            return [dict(r) for r in rows]

    def _collect_access_logs(self, org_id: str, start_date: datetime, end_date: datetime) -> List[dict]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT al.id, al.user_id, al.action, al.resource, al.created_at, u.email
                FROM audit_logs al
                LEFT JOIN users u ON u.id = al.user_id
                LEFT JOIN organization_members om ON om.user_id = al.user_id
                WHERE om.org_id = ? AND al.action IN ('login', 'logout', 'api_call')
                AND al.created_at BETWEEN ? AND ?
                ORDER BY al.created_at DESC
                """,
                (org_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
            return [dict(r) for r in rows]

    def _collect_metrics(self, org_id: str, start_date: datetime, end_date: datetime) -> List[dict]:
        members = []
        with get_db() as conn:
            rows = conn.execute(
                "SELECT user_id FROM organization_members WHERE org_id = ?",
                (org_id,),
            ).fetchall()
            members = [r["user_id"] for r in rows]

        metrics = []
        cutoff = start_date.isoformat()
        with get_db() as conn:
            for user_id in members:
                rows = conn.execute(
                    "SELECT * FROM usage WHERE user_id = ? AND created_at BETWEEN ? AND ?",
                    (user_id, cutoff, end_date.isoformat()),
                ).fetchall()
                for r in rows:
                    metrics.append(dict(r))
        return metrics

    def _collect_configuration(self, org_id: str, start_date: datetime, end_date: datetime) -> List[dict]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sso_connections WHERE org_id = ?",
                (org_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def collect_all(self, org_id: str, start_date: datetime, end_date: datetime) -> Dict[str, List[dict]]:
        return {etype: self.collect(etype, org_id, start_date, end_date) for etype in self.evidence_types}
