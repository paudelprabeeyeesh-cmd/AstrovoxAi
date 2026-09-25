import uuid
from datetime import datetime, timezone

from .database import get_db


def create_affiliate(user_id: str, name: str, email: str) -> dict:
    affiliate_id = str(uuid.uuid4())
    code = f"AFF-{user_id[:6].upper()}-{uuid.uuid4().hex[:6].upper()}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO affiliates (id, user_id, name, email, code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (affiliate_id, user_id, name, email, code, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": affiliate_id, "code": code}


def list_affiliates(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, email, code, created_at FROM affiliates WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "email": r["email"],
                "code": r["code"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def track_conversion(affiliate_code: str, amount: float):
    with get_db() as conn:
        conn.execute(
            "UPDATE affiliates SET conversions = conversions + 1, revenue = revenue + ? WHERE code = ?",
            (amount, affiliate_code),
        )
        conn.commit()
