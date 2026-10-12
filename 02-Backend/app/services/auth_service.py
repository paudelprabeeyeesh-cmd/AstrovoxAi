"""Core authentication service."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.database import get_db
from sqlalchemy import text


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_login_attempts(conn) -> None:
    """Create or migrate the login_attempts table.

    Shared with app/services/auth/auth.py; see
    app/services/login_attempt_schema.py for why the schema lives in one
    place. Without it this insert raised
    "table login_attempts has no column named lockout_until" whenever the
    other module had created the narrower table first.
    """
    from app.services.login_attempt_schema import ensure_login_attempts_table

    ensure_login_attempts_table(conn)


def create_user(email: str, password: str, full_name: Optional[str] = None, role: str = "user", plan: str = "free") -> dict:
    user_id = str(uuid.uuid4())
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    with get_db() as conn:
        conn.execute(
            text("INSERT INTO users (id, email, password_hash, role, plan, email_verified, created_at) VALUES (:p1, :p2, :p3, :p4, :p5, :p6, :p7)"),
            {"p1": user_id, "p2": email.lower(), "p3": password_hash, "p4": role, "p5": plan, "p6": 0, "p7": _now().isoformat()},
        )
        conn.commit()
    return {"id": user_id, "email": email.lower(), "role": role, "plan": plan, "email_verified": False}


def get_user_by_email(email: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE email = :email LIMIT 1"),
            {"email": email.lower()},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE id = :user_id LIMIT 1"),
            {"user_id": user_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def verify_password(user: dict, password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == user["password_hash"]


def update_password(user_id: str, new_password: str) -> bool:
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    with get_db() as conn:
        conn.execute(
            text("UPDATE users SET password_hash=:password_hash WHERE id=:id"),
            {"password_hash": password_hash, "id": user_id},
        )
        conn.commit()
    return True


def update_email_verified(user_id: str, verified: bool = True) -> bool:
    with get_db() as conn:
        conn.execute(
            text("UPDATE users SET email_verified=:email_verified WHERE id=:id"),
            {"email_verified": 1 if verified else 0, "id": user_id},
        )
        conn.commit()
    return True


def record_login_attempt(ip: str, success: bool, lockout_until: Optional[str] = None) -> None:
    with get_db() as conn:
        _ensure_login_attempts(conn)
        conn.execute(
            text(
                "INSERT INTO login_attempts (id, ip, email, success, lockout_until, created_at) "
                "VALUES (:id, :ip, :email, :success, :lockout_until, :created_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "ip": ip,
                "email": "",
                "success": 1 if success else 0,
                "lockout_until": lockout_until,
                "created_at": _now().isoformat(),
            },
        )
        conn.commit()


def check_login_lockout(ip: str) -> Optional[str]:
    cutoff = (_now() - timedelta(minutes=15)).isoformat()
    with get_db() as conn:
        # .mappings() so the aggregate row is addressable by column name.
        row = conn.execute(
            text(
                "SELECT COUNT(*) AS c FROM login_attempts "
                "WHERE ip = :ip AND success = 0 AND created_at > :cutoff"
            ),
            {"ip": ip, "cutoff": cutoff},
        ).mappings().fetchone()
    if row and row["c"] >= 5:
        return "Too many failed login attempts. Try again in 15 minutes."
    return None
