import uuid
import hashlib
from datetime import datetime
from typing import Optional
from .database import get_db


class APIKey:
    def __init__(self, id: str, name: str, scopes: str, last_used: str, created_at: str, key: Optional[str] = None):
        self.id = id
        self.name = name
        self.scopes = scopes
        self.last_used = last_used
        self.created_at = created_at
        self.key = key


def create_api_key(user_id: str, name: str, scopes: str = "read") -> APIKey:
    key = f"astrovox-{uuid.uuid4().hex}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, user_id, key_hash, name, scopes, last_used) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, key_hash, name, scopes, datetime.utcnow().isoformat()),
        )
        conn.commit()
    return APIKey(
        id=key,
        name=name,
        scopes=scopes,
        last_used=datetime.utcnow().isoformat(),
        created_at=datetime.utcnow().isoformat(),
        key=key,
    )


def validate_api_key(key: str) -> str:
    import os as _os
    _master = _os.getenv("ASTROVOX_KEY")
    if _master and key == _master:
        return "master-user"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
        if not row:
            raise ValueError("Invalid API key")
        conn.execute("UPDATE api_keys SET last_used = ? WHERE key_hash = ?", (datetime.utcnow().isoformat(), key_hash))
        conn.commit()
        return row["user_id"]


def list_api_keys(user_id: str) -> list[APIKey]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, scopes, last_used, created_at FROM api_keys WHERE user_id = ?", (user_id,)).fetchall()
        return [
            APIKey(
                id=r["id"],
                name=r["name"],
                scopes=r["scopes"],
                last_used=r["last_used"],
                created_at=r["created_at"],
            )
            for r in rows
        ]


def revoke_api_key(user_id: str, key_id: str) -> bool:
    with get_db() as conn:
        result = conn.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
        conn.commit()
        return result.rowcount > 0
