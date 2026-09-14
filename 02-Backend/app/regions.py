import uuid
from datetime import datetime

from .database import get_db


def create_region(name: str, code: str, config: str) -> dict:
    region_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO regions (id, name, code, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (region_id, name, code, config, datetime.utcnow().isoformat()),
        )
        conn.commit()
    return {"id": region_id, "name": name, "code": code}


def list_regions() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, code, config, created_at FROM regions ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "code": r["code"],
                "config": r["config"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
