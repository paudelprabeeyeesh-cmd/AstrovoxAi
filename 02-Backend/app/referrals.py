
import uuid
from datetime import datetime, timezone
from .database import get_db

def create_referral(user_id: str, email: str) -> dict:
    code = f"REF-{user_id[:6].upper()}-{uuid.uuid4().hex[:6].upper()}"
    with get_db() as conn:
        conn.execute("INSERT INTO referrals (id, user_id, code, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, code, email, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return {"code": code, "url": f"https://astrovox.ai/signup?ref={code}"}

def track_signup(referral_code: str, new_user_id: str):
    with get_db() as conn:
        conn.execute("UPDATE referrals SET signup_user_id = ?, signup_at = ? WHERE code = ?",
            (new_user_id, datetime.now(timezone.utc).isoformat(), referral_code))
        conn.commit()

def get_referral_stats(user_id: str) -> dict:
    with get_db() as conn:
        invitations = conn.execute("SELECT COUNT(*) as c FROM referrals WHERE user_id = ?", (user_id,)).fetchone()["c"]
        conversions = conn.execute("SELECT COUNT(*) as c FROM referrals WHERE user_id = ? AND signup_user_id IS NOT NULL", (user_id,)).fetchone()["c"]
    k_factor = round(conversions / invitations, 4) if invitations > 0 else 0.0
    rewards = conversions // 3
    return {"invitations": invitations, "conversions": conversions, "k_factor": k_factor, "rewards_earned": rewards, "revenue": conversions * 5.0}
