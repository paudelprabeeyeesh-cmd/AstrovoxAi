import uuid
from datetime import datetime

from .database import get_db


def create_vertical(name: str, description: str, config: str) -> dict:
    vertical_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO verticals (id, name, description, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (vertical_id, name, description, config, datetime.utcnow().isoformat()),
        )
        conn.commit()
    return {"id": vertical_id, "name": name}


def list_verticals() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, config, created_at FROM verticals ORDER BY created_at DESC"
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
