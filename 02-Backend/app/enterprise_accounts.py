import json
import uuid
from datetime import datetime
from .database import get_db

def create_enterprise_account(company: str, contact_email: str, plan: str = "enterprise") -> dict:
    account_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO enterprise_accounts (id, company, contact_email, plan, created_at) VALUES (?, ?, ?, ?, ?)",
                     (account_id, company, contact_email, plan, datetime.utcnow().isoformat()))
        conn.commit()
    return {"id": account_id, "company": company, "plan": plan}

def list_enterprise_accounts() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, company, contact_email, plan, created_at FROM enterprise_accounts ORDER BY created_at DESC").fetchall()
        return [{"id": r["id"], "company": r["company"], "contact_email": r["contact_email"], "plan": r["plan"], "created_at": r["created_at"]} for r in rows]
