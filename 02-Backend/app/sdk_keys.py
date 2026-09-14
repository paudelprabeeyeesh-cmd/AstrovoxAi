import json
import uuid
from datetime import datetime

from .database import get_db


def create_sdk_key(user_id: str, name: str) -> dict:
    key = f"astrovox-sdk-{uuid.uuid4().hex}"
    key_hash = __import__('hashlib').sha256(key.encode()).hexdigest()
    with get_db() as conn:
        conn.execute("INSERT INTO sdk_keys (id, user_id, name, key_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                     (str(uuid.uuid4()), user_id, name, key_hash, datetime.utcnow().isoformat()))
        conn.commit()
    return {"key": key, "name": name}

def list_sdk_keys(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, created_at FROM sdk_keys WHERE user_id = ?", (user_id,)).fetchall()
        return [{"id": r["id"], "name": r["name"], "created_at": r["created_at"]} for r in rows]
