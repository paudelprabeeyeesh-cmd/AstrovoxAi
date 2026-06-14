import os
import json
import threading
from datetime import datetime
from typing import List, Dict, Any

# Simple JSON-backed memory for conversations.
# File is stored next to this module as `chat_history_db.json`.

LOCK = threading.Lock()
DB_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history_db.json")


def _ensure_db() -> None:
    if not os.path.exists(DB_FILENAME):
        with open(DB_FILENAME, "w", encoding="utf-8") as fh:
            json.dump({}, fh)


def _read_db() -> Dict[str, Any]:
    _ensure_db()
    with LOCK:
        with open(DB_FILENAME, "r", encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except Exception:
                return {}


def _write_db(data: Dict[str, Any]) -> None:
    with LOCK:
        with open(DB_FILENAME, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)


def get_history(conversation_id: str) -> List[Dict[str, Any]]:
    """Return list of message dicts for conversation_id. Each item: {role, message, timestamp}."""
    db = _read_db()
    return db.get(conversation_id, [])


def save_message_pair(conversation_id: str, user_message: str, ai_message: str) -> None:
    """Append a user/assistant message pair to the conversation history."""
    db = _read_db()
    entry_user = {"role": "user", "message": user_message, "timestamp": datetime.utcnow().isoformat() + "Z"}
    entry_ai = {"role": "assistant", "message": ai_message, "timestamp": datetime.utcnow().isoformat() + "Z"}
    conv = db.get(conversation_id, [])
    conv.append(entry_user)
    conv.append(entry_ai)
    db[conversation_id] = conv
    _write_db(db)


def clear_conversation(conversation_id: str) -> None:
    db = _read_db()
    if conversation_id in db:
        db.pop(conversation_id)
        _write_db(db)


def list_conversations() -> List[str]:
    db = _read_db()
    return list(db.keys())


if __name__ == "__main__":
    print("Memory module initialized. DB file:", DB_FILENAME)