
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_security_certification(org_id: str, certification_name: str, certification_body: str, issued_at: str, expires_at: Optional[str] = None, certificate_url: Optional[str] = None, scope: Optional[str] = None) -> dict:
    cert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO security_certifications (id, org_id, certification_name, certification_body, issued_at, expires_at, status, certificate_url, scope, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cert_id, org_id, certification_name, certification_body, issued_at, expires_at, "active", certificate_url, scope, "{}", now),
        )
        conn.commit()
    log_action(None, "create_security_certification", f"org:{org_id}", {"certification_name": certification_name})
    return {"id": cert_id, "org_id": org_id, "certification_name": certification_name, "certification_body": certification_body, "status": "active"}


def get_security_certification(cert_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM security_certifications WHERE id = ?", (cert_id,)).fetchone()
        return dict(row) if row else None


def list_security_certifications(org_id: str, status: Optional[str] = None) -> List[dict]:
    with get_db() as conn:
        query = "SELECT * FROM security_certifications WHERE org_id = ?"
        params = [org_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY issued_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_security_certification(cert_id: str, **kwargs) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM security_certifications WHERE id = ?", (cert_id,)).fetchone()
        if not row:
            raise ValueError("Certification not found")
        updates = {}
        for key in ["certification_name", "certification_body", "issued_at", "expires_at", "status", "certificate_url", "scope"]:
            if key in kwargs:
                updates[key] = kwargs[key]
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [cert_id]
        conn.execute(f"UPDATE security_certifications SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_security_certification(cert_id)


def delete_security_certification(cert_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM security_certifications WHERE id = ?", (cert_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        log_action(requester_id, "delete_security_certification", f"cert:{cert_id}", {})
    return deleted


def check_expiring_certifications(org_id: str, days_ahead: int = 30) -> List[dict]:
    with get_db() as conn:
        future = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()
        rows = conn.execute(
            "SELECT * FROM security_certifications WHERE org_id = ? AND expires_at IS NOT NULL AND expires_at <= ? AND status = 'active'",
            (org_id, future),
        ).fetchall()
        return [dict(r) for r in rows]
