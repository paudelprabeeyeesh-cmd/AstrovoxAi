"""Magic link authentication service."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import get_db


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_magic_link(user_id: str, email: str, expires_in_minutes: int = 15) -> dict:
    token = secrets.token_urlsafe(32)
    token_hash = _hash(token)
    expires_at = (_now() + timedelta(minutes=expires_in_minutes)).isoformat()
    link_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO magic_links (id, user_id, email, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (link_id, user_id, email.lower(), token_hash, expires_at, _now().isoformat()),
        )
        conn.commit()
    return {"id": link_id, "email": email.lower(), "token": token, "expires_at": expires_at}


def verify_magic_link(token: str) -> Optional[dict]:
    token_hash = _hash(token)
    row = get_db().__enter__().execute(
        "SELECT * FROM magic_links WHERE token_hash=? AND used=0 AND expires_at > ?",
        (token_hash, _now().isoformat()),
    ).fetchone()
    if row:
        with get_db() as conn:
            conn.execute("UPDATE magic_links SET used=1 WHERE id=?", (row["id"],))
            conn.commit()
    return dict(row) if row else None


def get_magic_link_by_email(email: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM magic_links WHERE email=? AND used=0 AND expires_at > ? ORDER BY created_at DESC LIMIT 1",
        (email.lower(), _now().isoformat()),
    ).fetchone()
    return dict(row) if row else None
