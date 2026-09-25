import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db


def create_enterprise_account(
    user_id: str, company: str, contact_email: str, plan: str = "enterprise"
) -> dict:
    account_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO enterprise_accounts (id, user_id, company, contact_email, plan, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, user_id, company, contact_email, plan, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": account_id, "company": company, "plan": plan}


def list_enterprise_accounts(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, company, contact_email, plan, created_at FROM enterprise_accounts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "company": r["company"],
                "contact_email": r["contact_email"],
                "plan": r["plan"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
