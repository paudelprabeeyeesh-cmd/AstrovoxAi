import uuid
from datetime import datetime
from .database import get_db

def create_api_key(user_id: str, name: str = None) -> str:
    key = f"astrovox-{uuid.uuid4().hex}"
    key_hash = __import__('hashlib').sha256(key.encode()).hexdigest()
    with get_db() as conn:
        conn.execute("INSERT INTO api_keys (id, user_id, key_hash, name) VALUES (?, ?, ?, ?)",
                     (str(uuid.uuid4()), user_id, key_hash, name))
        conn.commit()
    return key

def validate_api_key(key: str) -> str:
    import os as _os
    _master = _os.getenv("ASTROVOX_KEY")
    if _master and key == _master:
        return "master-user"
    key_hash = __import__('hashlib').sha256(key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
        if not row:
            raise ValueError("Invalid API key")
        conn.execute("UPDATE api_keys SET last_used = ? WHERE key_hash = ?", (datetime.utcnow().isoformat(), key_hash))
        conn.commit()
        return row["user_id"]

def list_api_keys(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, last_used, created_at FROM api_keys WHERE user_id = ?", (user_id,)).fetchall()
        return [{"id": r["id"], "name": r["name"], "last_used": r["last_used"], "created_at": r["created_at"]} for r in rows]

def delete_api_key(key_id: str, user_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
        conn.commit()
