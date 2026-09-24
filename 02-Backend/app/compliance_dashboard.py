
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_compliance_report(org_id: str, report_type: str, framework: str, period_start: str, period_end: str, generated_by: Optional[str] = None) -> dict:
    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO compliance_reports (id, org_id, report_type, framework, period_start, period_end, status, generated_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (report_id, org_id, report_type, framework, period_start, period_end, "generated", generated_by, now),
        )
        conn.commit()
    log_action(generated_by, "create_compliance_report", f"org:{org_id}", {"framework": framework, "report_type": report_type})
    return {"id": report_id, "org_id": org_id, "framework": framework, "report_type": report_type, "status": "generated"}


def get_compliance_report(report_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM compliance_reports WHERE id = ?", (report_id,)).fetchone()
        return dict(row) if row else None


def list_compliance_reports(org_id: str, framework: Optional[str] = None, report_type: Optional[str] = None) -> List[dict]:
    with get_db() as conn:
        query = "SELECT * FROM compliance_reports WHERE org_id = ?"
        params = [org_id]
        if framework:
            query += " AND framework = ?"
            params.append(framework)
        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def generate_gdpr_report(org_id: str, period_start: str, period_end: str, generated_by: Optional[str] = None) -> dict:
    return create_compliance_report(org_id, "gdpr_audit", "GDPR", period_start, period_end, generated_by)


def generate_ccpa_report(org_id: str, period_start: str, period_end: str, generated_by: Optional[str] = None) -> dict:
    return create_compliance_report(org_id, "ccpa_audit", "CCPA", period_start, period_end, generated_by)


def get_compliance_dashboard(org_id: str) -> dict:
    with get_db() as conn:
        total_reports = conn.execute("SELECT COUNT(*) as c FROM compliance_reports WHERE org_id = ?", (org_id,)).fetchone()["c"]
        gdpr_reports = conn.execute("SELECT COUNT(*) as c FROM compliance_reports WHERE org_id = ? AND framework = 'GDPR'", (org_id,)).fetchone()["c"]
        ccpa_reports = conn.execute("SELECT COUNT(*) as c FROM compliance_reports WHERE org_id = ? AND framework = 'CCPA'", (org_id,)).fetchone()["c"]
        total_certs = conn.execute("SELECT COUNT(*) as c FROM security_certifications WHERE org_id = ? AND status = 'active'", (org_id,)).fetchone()["c"]
        open_tickets = conn.execute("SELECT COUNT(*) as c FROM support_tickets WHERE org_id = ? AND status = 'open'", (org_id,)).fetchone()["c"]
        total_deletions = conn.execute("SELECT COUNT(*) as c FROM data_deletion_requests WHERE org_id = ?", (org_id,)).fetchone()["c"]
        pending_deletions = conn.execute("SELECT COUNT(*) as c FROM data_deletion_requests WHERE org_id = ? AND status = 'pending'", (org_id,)).fetchone()["c"]
        active_policies = conn.execute("SELECT COUNT(*) as c FROM data_retention_policies WHERE org_id = ? AND status = 'active'", (org_id,)).fetchone()["c"]
        return {
            "org_id": org_id,
            "compliance_reports": {"total": total_reports, "gdpr": gdpr_reports, "ccpa": ccpa_reports},
            "security_certifications": {"active": total_certs},
            "support_tickets": {"open": open_tickets},
            "data_deletion": {"total": total_deletions, "pending": pending_deletions},
            "retention_policies": {"active": active_policies},
        }


def update_compliance_report(report_id: str, findings: Optional[str] = None, recommendations: Optional[str] = None, status: Optional[str] = None) -> dict:
    with get_db() as conn:
        updates = {}
        if findings is not None:
            updates["findings"] = findings
        if recommendations is not None:
            updates["recommendations"] = recommendations
        if status is not None:
            updates["status"] = status
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [report_id]
            conn.execute(f"UPDATE compliance_reports SET {set_clause} WHERE id = ?", values)
            conn.commit()
    return get_compliance_report(report_id)
