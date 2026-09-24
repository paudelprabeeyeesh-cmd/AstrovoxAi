"""Session management service."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.database import get_db


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(user_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
    session_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    expires_at = (_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()
    session_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_sessions (id, user_id, session_token, refresh_token, ip_address, user_agent, expires_at, last_activity_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, user_id, session_token, refresh_token, ip_address, user_agent, expires_at, _now().isoformat(), _now().isoformat()),
        )
        conn.commit()
    return {
        "id": session_id,
        "user_id": user_id,
        "session_token": session_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }


def get_session(session_token: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM user_sessions WHERE session_token=? AND expires_at > ?",
        (session_token, _now().isoformat()),
    ).fetchone()
    return dict(row) if row else None


def get_session_by_refresh_token(refresh_token: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM user_sessions WHERE refresh_token=? AND expires_at > ?",
        (refresh_token, _now().isoformat()),
    ).fetchone()
    return dict(row) if row else None


def refresh_session(refresh_token: str) -> Optional[dict]:
    session = get_session_by_refresh_token(refresh_token)
    if not session:
        return None
    new_session_token = secrets.token_urlsafe(32)
    new_refresh_token = secrets.token_urlsafe(32)
    expires_at = (_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE user_sessions SET session_token=?, refresh_token=?, expires_at=?, last_activity_at=? WHERE id=?",
            (new_session_token, new_refresh_token, expires_at, _now().isoformat(), session["id"]),
        )
        conn.commit()
    return {
        "id": session["id"],
        "user_id": session["user_id"],
        "session_token": new_session_token,
        "refresh_token": new_refresh_token,
        "expires_at": expires_at,
    }


def delete_session(session_token: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM user_sessions WHERE session_token=?", (session_token,))
        conn.commit()
    return cur.rowcount > 0


def delete_all_user_sessions(user_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
        conn.commit()
    return True


def update_session_activity(session_token: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE user_sessions SET last_activity_at=? WHERE session_token=?",
            (_now().isoformat(), session_token),
        )
        conn.commit()


def get_user_sessions(user_id: str) -> list:
    rows = get_db().__enter__().execute(
        "SELECT * FROM user_sessions WHERE user_id=? ORDER BY last_activity_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]
