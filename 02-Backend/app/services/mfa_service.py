"""Multi-factor authentication service."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.database import get_db


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def setup_mfa(user_id: str) -> dict:
    secret = secrets.token_hex(16)
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO mfa_secrets (id, user_id, secret, enabled, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, secret, 0, _now().isoformat()),
        )
        conn.commit()
    return {"secret": secret}


def get_mfa_secret(user_id: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM mfa_secrets WHERE user_id=?",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def enable_mfa(user_id: str) -> bool:
    with get_db() as conn:
        conn.execute("UPDATE mfa_secrets SET enabled=1 WHERE user_id=?", (user_id,))
        conn.commit()
    return True


def disable_mfa(user_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM mfa_secrets WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM mfa_backup_codes WHERE user_id=?", (user_id,))
        conn.commit()
    return True


def generate_backup_codes(user_id: str, count: int = 10) -> List[str]:
    codes = [secrets.token_hex(4) for _ in range(count)]
    with get_db() as conn:
        for code in codes:
            code_hash = _hash(code)
            conn.execute(
                "INSERT INTO mfa_backup_codes (id, user_id, code_hash, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, code_hash, _now().isoformat()),
            )
        conn.commit()
    return codes


def verify_totp(secret: str, code: str) -> bool:
    import hmac
    import struct
    import time
    try:
        key = bytes.fromhex(secret)
        tm = int(time.time()) // 30
        for offset in [0, -1, 1]:
            tm_offset = tm + offset
            msg = struct.pack(">Q", tm_offset)
            digest = hmac.new(key, msg, "sha1").digest()
            offset_val = digest[-1] & 0xF
            code_val = struct.unpack(">I", digest[offset_val:offset_val + 4])[0]
            code_val = (code_val & 0x7FFFFFFF) % 1000000
            if f"{code_val:06d}" == code.strip():
                return True
    except Exception:
        pass
    return False


def verify_mfa_code(user_id: str, code: str) -> bool:
    mfa = get_mfa_secret(user_id)
    if not mfa or not mfa.get("enabled"):
        return False
    return verify_totp(mfa["secret"], code)


def verify_backup_code(user_id: str, code: str) -> bool:
    code_hash = _hash(code)
    row = get_db().__enter__().execute(
        "SELECT * FROM mfa_backup_codes WHERE user_id=? AND code_hash=? AND used=0",
        (user_id, code_hash),
    ).fetchone()
    if row:
        with get_db() as conn:
            conn.execute("UPDATE mfa_backup_codes SET used=1 WHERE id=?", (row["id"],))
            conn.commit()
        return True
    return False


def verify_mfa(user_id: str, code: str, backup_code: Optional[str] = None) -> bool:
    if backup_code:
        return verify_backup_code(user_id, backup_code)
    return verify_mfa_code(user_id, code)


def is_mfa_enabled(user_id: str) -> bool:
    mfa = get_mfa_secret(user_id)
    return bool(mfa and mfa.get("enabled"))
