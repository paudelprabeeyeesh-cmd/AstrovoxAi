
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_custom_domain(org_id: str, domain: str) -> dict:
    domain_id = str(uuid.uuid4())
    verification_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO custom_domains (id, org_id, domain, verification_token, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (domain_id, org_id, domain.lower(), verification_token, "pending", now, now),
        )
        conn.execute("UPDATE organizations SET custom_domain = ?, updated_at = ? WHERE id = ?", (domain.lower(), now, org_id))
        conn.commit()
    log_action(None, "create_custom_domain", f"org:{org_id}", {"domain": domain})
    return {"id": domain_id, "org_id": org_id, "domain": domain.lower(), "verification_token": verification_token, "status": "pending"}


def verify_domain(domain_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM custom_domains WHERE id = ?", (domain_id,)).fetchone()
        if not row:
            raise ValueError("Domain not found")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE custom_domains SET verified = 1, status = 'active', updated_at = ? WHERE id = ?", (now, domain_id))
        conn.commit()
    log_action(None, "verify_custom_domain", f"domain:{domain_id}", {})
    return get_custom_domain(domain_id)


def get_custom_domain(domain_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM custom_domains WHERE id = ?", (domain_id,)).fetchone()
        return dict(row) if row else None


def list_custom_domains(org_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM custom_domains WHERE org_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()
        return [dict(r) for r in rows]


def update_ssl_status(domain_id: str, ssl_status: str, cert_path: Optional[str] = None, key_path: Optional[str] = None) -> dict:
    with get_db() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE custom_domains SET ssl_status = ?, ssl_cert_path = ?, ssl_key_path = ?, updated_at = ? WHERE id = ?",
            (ssl_status, cert_path, key_path, now, domain_id),
        )
        conn.commit()
    return get_custom_domain(domain_id)


def delete_custom_domain(domain_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT org_id, domain FROM custom_domains WHERE id = ?", (domain_id,)).fetchone()
        if not row:
            return False
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE organizations SET custom_domain = NULL, updated_at = ? WHERE id = ?", (now, row["org_id"]))
        cur = conn.execute("DELETE FROM custom_domains WHERE id = ?", (domain_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        log_action(requester_id, "delete_custom_domain", f"domain:{domain_id}", {})
    return deleted


def get_domain_by_domain(domain: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM custom_domains WHERE domain = ?", (domain.lower(),)).fetchone()
        return dict(row) if row else None
