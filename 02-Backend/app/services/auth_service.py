"""Core authentication service."""
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


def create_user(email: str, password: str, full_name: Optional[str] = None, role: str = "user", plan: str = "free") -> dict:
    user_id = str(uuid.uuid4())
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    get_db().__enter__().execute(
        "INSERT INTO users (id, email, password_hash, role, plan, email_verified, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, email.lower(), password_hash, role, plan, 0, _now().isoformat()),
    )
    get_db().__enter__().commit()
    return {"id": user_id, "email": email.lower(), "role": role, "plan": plan, "email_verified": False}


def get_user_by_email(email: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM users WHERE email=? LIMIT 1", (email.lower(),)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM users WHERE id=? LIMIT 1", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def verify_password(user: dict, password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == user["password_hash"]


def update_password(user_id: str, new_password: str) -> bool:
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    get_db().__enter__().execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (password_hash, user_id),
    )
    get_db().__enter__().commit()
    return True


def update_email_verified(user_id: str, verified: bool = True) -> bool:
    get_db().__enter__().execute(
        "UPDATE users SET email_verified=? WHERE id=?",
        (1 if verified else 0, user_id),
    )
    get_db().__enter__().commit()
    return True


def record_login_attempt(ip: str, success: bool, lockout_until: Optional[str] = None) -> None:
    get_db().__enter__().execute(
        "INSERT INTO login_attempts (id, ip, success, lockout_until, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), ip, 1 if success else 0, lockout_until, _now().isoformat()),
    )
    get_db().__enter__().commit()


def check_login_lockout(ip: str) -> Optional[str]:
    cutoff = (_now() - timedelta(minutes=15)).isoformat()
    row = get_db().__enter__().execute(
        "SELECT COUNT(*) as c FROM login_attempts WHERE ip=? AND success=0 AND created_at > ?",
        (ip, cutoff),
    ).fetchone()
    if row and row["c"] >= 5:
        return "Too many failed login attempts. Try again in 15 minutes."
    return None
