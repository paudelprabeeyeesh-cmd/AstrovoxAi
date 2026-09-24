
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def generate_api_key() -> tuple[str, str, str]:
    raw_key = f"astrovox_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix


def create_api_key(org_id: str, name: str, user_id: Optional[str] = None, permissions: Optional[List[str]] = None, expires_in_days: Optional[int] = None) -> dict:
    raw_key, key_hash, key_prefix = generate_api_key()
    key_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=expires_in_days)).isoformat() if expires_in_days else None
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, org_id, user_id, name, key_hash, key_prefix, permissions, status, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (key_id, org_id, user_id, name, key_hash, key_prefix, str(permissions or []), "active", expires_at, now.isoformat()),
        )
        conn.commit()
    log_action(user_id, "create_api_key", f"org:{org_id}", {"name": name})
    return {"id": key_id, "name": name, "key_prefix": key_prefix, "raw_key": raw_key, "permissions": permissions or [], "expires_at": expires_at}


def get_api_key(key_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT id, org_id, user_id, name, key_prefix, permissions, last_used_at, expires_at, status, created_at FROM api_keys WHERE id = ?", (key_id,)).fetchone()
        return dict(row) if row else None


def list_api_keys(org_id: str, user_id: Optional[str] = None) -> List[dict]:
    with get_db() as conn:
        if user_id:
            rows = conn.execute("SELECT id, org_id, user_id, name, key_prefix, permissions, last_used_at, expires_at, status, created_at FROM api_keys WHERE org_id = ? AND user_id = ?", (org_id, user_id)).fetchall()
        else:
            rows = conn.execute("SELECT id, org_id, user_id, name, key_prefix, permissions, last_used_at, expires_at, status, created_at FROM api_keys WHERE org_id = ?", (org_id,)).fetchall()
        return [dict(r) for r in rows]


def validate_api_key(raw_key: str) -> Optional[dict]:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
        if not row:
            return None
        if row["status"] != "active":
            return None
        if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            return None
        conn.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), row["id"]))
        conn.commit()
        return dict(row)


def revoke_api_key(key_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("UPDATE api_keys SET status = 'revoked' WHERE id = ?", (key_id,))
        conn.commit()
        revoked = cur.rowcount > 0
    if revoked:
        log_action(requester_id, "revoke_api_key", f"key:{key_id}", {})
    return revoked


def delete_api_key(key_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        log_action(requester_id, "delete_api_key", f"key:{key_id}", {})
    return deleted
