"""Device management service."""
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


def create_device(user_id: str, name: str, fingerprint: str, device_type: str = "unknown", platform: Optional[str] = None, browser: Optional[str] = None) -> dict:
    device_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO devices (id, user_id, name, device_type, platform, browser, fingerprint, last_seen_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (device_id, user_id, name, device_type, platform, browser, fingerprint, _now().isoformat(), _now().isoformat()),
        )
        conn.commit()
    return {"id": device_id, "user_id": user_id, "name": name, "device_type": device_type, "platform": platform, "browser": browser, "fingerprint": fingerprint}


def get_devices(user_id: str) -> List[dict]:
    rows = get_db().__enter__().execute(
        "SELECT * FROM devices WHERE user_id=? ORDER BY last_seen_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_device_by_fingerprint(fingerprint: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM devices WHERE fingerprint=?",
        (fingerprint,),
    ).fetchone()
    return dict(row) if row else None


def get_device(device_id: str, user_id: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM devices WHERE id=? AND user_id=?",
        (device_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def trust_device(device_id: str, user_id: str) -> bool:
    with get_db() as conn:
        conn.execute("UPDATE devices SET trusted=1, last_seen_at=? WHERE id=? AND user_id=?", (_now().isoformat(), device_id, user_id))
        conn.commit()
    return True


def untrust_device(device_id: str, user_id: str) -> bool:
    with get_db() as conn:
        conn.execute("UPDATE devices SET trusted=0 WHERE id=? AND user_id=?", (device_id, user_id))
        conn.commit()
    return True


def delete_device(device_id: str, user_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM devices WHERE id=? AND user_id=?", (device_id, user_id))
        conn.commit()
    return cur.rowcount > 0


def update_device_last_seen(device_id: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE devices SET last_seen_at=? WHERE id=?", (_now().isoformat(), device_id))
        conn.commit()
