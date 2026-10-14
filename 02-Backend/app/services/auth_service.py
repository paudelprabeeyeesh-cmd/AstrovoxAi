"""Core authentication service."""
import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.database import get_db
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Password hashing uses salted, memory-hard scrypt from the standard library
# (P0-1). argon2-cffi is not installed in this environment, so the stdlib
# scrypt fallback is used deliberately: it adds no new dependency. Every call
# draws a fresh 16-byte salt, so the same password hashes to a different value
# each time. Records written before this change are a bare 64-hex SHA-256
# digest; they still verify and are transparently upgraded on successful login.
_SCRYPT_PREFIX = "scrypt"
_SCRYPT_N = 2 ** 14          # 16384 -> ~16 MiB per hash
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_SALT_BYTES = 16
_SCRYPT_DKLEN = 32
_SCRYPT_MAXMEM = 64 * 1024 * 1024


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str) -> str:
    """Salted, memory-hard scrypt digest in ``scrypt$N$r$p$salt$hash`` form.

    The cost parameters and salt are embedded so a record stays verifiable
    even after the module defaults are raised later.
    """
    salt = secrets.token_bytes(_SCRYPT_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return (
        f"{_SCRYPT_PREFIX}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}"
        f"${salt.hex()}${digest.hex()}"
    )


# Public name. ``app.auth.hash_password`` delegates here through
# ``_hash_password``; both names resolve to the same salted scrypt hash.
hash_password = _hash_password


def _verify_scrypt(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) != 6:
        return False
    _, n, r, p, salt_hex, hash_hex = parts
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=_SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def _is_legacy_sha256(stored: str) -> bool:
    """A pre-hardening record is a bare 64-char lowercase-hex SHA-256 digest."""
    return len(stored) == 64 and all(c in "0123456789abcdef" for c in stored)


def _store_password_hash(user_id: str, new_hash: str) -> None:
    with get_db() as conn:
        conn.execute(
            text("UPDATE users SET password_hash=:h WHERE id=:id"),
            {"h": new_hash, "id": user_id},
        )
        conn.commit()


def _rehash_best_effort(user_id: str | None, password: str) -> None:
    """Upgrade a verified legacy record to scrypt without breaking login."""
    if not user_id:
        return
    try:
        _store_password_hash(user_id, _hash_password(password))
    except Exception:
        logger.debug("password rehash skipped; storage update failed")


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
    password_hash = _hash_password(password)
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
    """Verify a password against the stored hash.

    Accepts both scrypt records (new) and bare 64-hex SHA-256 records
    (pre-hardening). A verified legacy record is transparently rehashed to
    scrypt; a verified scrypt record is rehashed only if the cost
    parameters have moved on. A wrong password never rewrites the record.
    """
    stored = (user or {}).get("password_hash") or ""
    if stored.startswith(f"{_SCRYPT_PREFIX}$"):
        if not _verify_scrypt(password, stored):
            return False
        if stored.split("$")[1:4] != [str(_SCRYPT_N), str(_SCRYPT_R), str(_SCRYPT_P)]:
            _rehash_best_effort((user or {}).get("id"), password)
        return True
    if _is_legacy_sha256(stored):
        legacy = hashlib.sha256(password.encode()).hexdigest()
        if hmac.compare_digest(legacy, stored):
            _rehash_best_effort((user or {}).get("id"), password)
            return True
        return False
    return False


def update_password(user_id: str, new_password: str) -> bool:
    password_hash = _hash_password(new_password)
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
