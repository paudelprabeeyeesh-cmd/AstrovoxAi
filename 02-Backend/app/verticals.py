import uuid
from datetime import datetime, timezone

from repositories.database.client import get_db


def create_vertical(user_id: str, name: str, description: str, config: str) -> dict:
    vertical_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO verticals (id, user_id, name, description, config, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (vertical_id, user_id, name, description, config, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": vertical_id, "name": name}


def list_verticals(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, config, created_at FROM verticals WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "config": r["config"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
