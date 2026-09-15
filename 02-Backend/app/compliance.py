import uuid
import json
from datetime import datetime
from .database import get_db


def ensure_consent_table():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS consent_records (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                granted INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def delete_user_data(user_id: str) -> dict:
    ensure_consent_table()
    with get_db() as conn:
        conn.execute("DELETE FROM interaction_labels WHERE interaction_id IN (SELECT id FROM interactions WHERE user_id = ?)", (user_id,))
        conn.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)", (user_id,))
        conn.execute("DELETE FROM team_members WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM templates WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM schedules WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM knowledge_docs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM workflows WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM tools WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM feedback WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM usage WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM teams WHERE owner_id = ?", (user_id,))
        conn.execute("DELETE FROM api_keys WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM marketplace_prompts WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM addons WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM ipo_metrics WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM referrals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM integrations WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM posts WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM comments WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM amas WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM case_studies WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM outreach WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM ad_campaigns WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM affiliates WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM enterprise_accounts WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM sso_connections WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM enterprise_audit_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM audit_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM custom_models WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM verticals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM regions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM sdk_keys WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM ma_targets WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM interactions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return {"deleted": True}


def export_user_data(user_id: str) -> dict:
    ensure_consent_table()
    data = {"user_id": user_id}
    with get_db() as conn:
        tables = [
            "users", "refresh_tokens", "memories", "conversations", "messages",
            "templates", "schedules", "knowledge_docs", "user_profiles",
            "workflows", "tools", "feedback", "usage", "subscriptions",
            "teams", "team_members", "api_keys", "marketplace_prompts",
            "addons", "ipo_metrics", "referrals", "integrations", "posts",
            "comments", "amas", "case_studies", "outreach", "ad_campaigns",
            "affiliates", "enterprise_accounts", "sso_connections",
            "enterprise_audit_logs", "audit_logs", "custom_models",
            "verticals", "regions", "sdk_keys", "ma_targets", "interactions",
            "interaction_labels", "consent_records"
        ]
        for table in tables:
            try:
                if table == "teams":
                    rows = conn.execute(f"SELECT * FROM {table} WHERE owner_id = ?", (user_id,)).fetchall()
                elif table == "interaction_labels":
                    rows = conn.execute(f"SELECT * FROM {table} WHERE interaction_id IN (SELECT id FROM interactions WHERE user_id = ?)", (user_id,)).fetchall()
                elif table == "messages":
                    rows = conn.execute(f"SELECT * FROM {table} WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)", (user_id,)).fetchall()
                else:
                    rows = conn.execute(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,)).fetchall()
                data[table] = [dict(r) for r in rows]
            except Exception:
                data[table] = []
    def _serialize(obj):
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialize(v) for v in obj]
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    return _serialize(data)


def record_consent(user_id: str, consent_type: str, granted: bool) -> dict:
    ensure_consent_table()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO consent_records (id, user_id, consent_type, granted) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, consent_type, 1 if granted else 0)
        )
        conn.commit()
    return {"recorded": True}
