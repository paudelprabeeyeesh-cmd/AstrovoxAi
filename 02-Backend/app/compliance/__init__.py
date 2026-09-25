
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
from ..database import get_db
from .collector import EvidenceCollector
from .reporter import ComplianceReporter
from .soc2 import SOC2Evidence
from .gdpr import GDPRCompliance


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
        conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM audit_logs WHERE user_id = ?", (user_id,))
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
            "teams", "team_members", "api_keys", "audit_logs", "consent_records"
        ]
        for table in tables:
            try:
                if table == "teams":
                    rows = conn.execute(f"SELECT * FROM {table} WHERE owner_id = ?", (user_id,)).fetchall()
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


__all__ = [
    "delete_user_data",
    "export_user_data",
    "record_consent",
    "EvidenceCollector",
    "ComplianceReporter",
    "SOC2Evidence",
    "GDPRCompliance",
]
