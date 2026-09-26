import uuid
import json
from datetime import datetime, timezone
from typing import Optional

from app.repositories.database.client import get_db


def create_enterprise_account(
    user_id: str, company: str, contact_email: str, plan: str = "enterprise", metadata: Optional[dict] = None
) -> dict:
    account_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO enterprise_accounts (id, user_id, company, contact_email, plan, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                user_id,
                company,
                contact_email,
                plan,
                json.dumps(metadata or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {"id": account_id, "company": company, "plan": plan}


def list_enterprise_accounts(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, company, contact_email, plan, metadata, created_at FROM enterprise_accounts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "company": r["company"],
            "contact_email": r["contact_email"],
            "plan": r["plan"],
            "metadata": json.loads(r["metadata"] or "{}"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def update_enterprise_account(account_id: str, **fields) -> Optional[dict]:
    allowed = {"company", "contact_email", "plan", "metadata"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [account_id]
    with get_db() as conn:
        conn.execute(f"UPDATE enterprise_accounts SET {set_clause} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM enterprise_accounts WHERE id = ?", (account_id,)).fetchone()
        conn.commit()
    return dict(row) if row else None
