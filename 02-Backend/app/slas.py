import uuid
from datetime import datetime, timezone

from .database import get_db


def create_sla(
    account_id: str, tier: str, uptime_guarantee: float, response_time_hours: int
) -> dict:
    sla_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO slas (id, account_id, tier, uptime_guarantee, response_time_hours, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                sla_id,
                account_id,
                tier,
                uptime_guarantee,
                response_time_hours,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {"id": sla_id, "tier": tier}


def get_sla(account_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, tier, uptime_guarantee, response_time_hours, created_at FROM slas WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        if not row:
            raise ValueError("SLA not found")
        return {
            "id": row["id"],
            "tier": row["tier"],
            "uptime_guarantee": row["uptime_guarantee"],
            "response_time_hours": row["response_time_hours"],
            "created_at": row["created_at"],
        }
