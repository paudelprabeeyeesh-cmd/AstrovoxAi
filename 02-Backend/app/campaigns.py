import uuid
from datetime import datetime, timezone

from .database import get_db


def create_ad_campaign(
    user_id: str, name: str, platform: str, budget: float, start_date: str, end_date: str
) -> dict:
    campaign_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ad_campaigns (id, user_id, name, platform, budget, start_date, end_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                campaign_id,
                user_id,
                name,
                platform,
                budget,
                start_date,
                end_date,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return {"id": campaign_id, "name": name}


def list_campaigns(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, platform, budget, start_date, end_date, created_at FROM ad_campaigns WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "platform": r["platform"],
                "budget": r["budget"],
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
