import json
from datetime import datetime
from .database import get_db
from .schemas import UserProfileOut

def get_profile(user_id: str) -> UserProfileOut:
    with get_db() as conn:
        row = conn.execute("SELECT user_id, style_json, updated_at FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return UserProfileOut(user_id=user_id, style_json=None, updated_at=datetime.utcnow())
        return UserProfileOut(user_id=row["user_id"], style_json=row["style_json"], updated_at=datetime.fromisoformat(row["updated_at"]))

def update_profile(user_id: str, style_json: str):
    with get_db() as conn:
        conn.execute("INSERT INTO user_profiles (user_id, style_json, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET style_json = excluded.style_json, updated_at = excluded.updated_at",
                     (user_id, style_json, datetime.utcnow().isoformat()))
        conn.commit()
