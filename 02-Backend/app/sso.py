import uuid
from datetime import datetime, timezone

from .core.encryption import encrypt, decrypt
from .database import get_db


def create_sso_connection(user_id: str, provider: str, config: str) -> dict:
    conn_id = str(uuid.uuid4())
    encrypted_config = encrypt(config)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sso_connections (id, user_id, provider, config, created_at) VALUES (?, ?, ?, ?, ?)",
            (conn_id, user_id, provider, encrypted_config, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": conn_id, "provider": provider}


def list_sso_connections(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, provider, config, created_at FROM sso_connections WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "provider": r["provider"],
                "config": decrypt(r["config"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]