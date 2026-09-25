import uuid
from datetime import datetime, timezone

from app.repositories.database.client import get_db


def create_custom_model(user_id: str, name: str, config: str) -> dict:
    model_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO custom_models (id, user_id, name, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (model_id, user_id, name, config, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": model_id, "name": name}


def list_custom_models(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, config, created_at FROM custom_models WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "config": r["config"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
