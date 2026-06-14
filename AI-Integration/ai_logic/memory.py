"""
Astravox AI Memory System - Flexible Backend
Supports both JSON and SQLite backends with automatic fallback.
"""

import os
from typing import List, Dict, Any, Optional

# Try to import both backends
try:
    from . import memory_sql
    HAS_SQL = True
except (ImportError, Exception):
    HAS_SQL = False
    memory_sql = None

try:
    # Legacy JSON-based memory (fallback)
    import json
    import threading
    from datetime import datetime
    
    LOCK = threading.Lock()
    DB_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history_db.json")
    
    def _ensure_json_db():
        if not os.path.exists(DB_FILENAME):
            with open(DB_FILENAME, "w") as f:
                json.dump({}, f)
    
    def _read_json_db():
        _ensure_json_db()
        with LOCK:
            with open(DB_FILENAME, "r") as f:
                try:
                    return json.load(f)
                except:
                    return {}
    
    def _write_json_db(data):
        with LOCK:
            with open(DB_FILENAME, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    HAS_JSON = True
except:
    HAS_JSON = False


# Determine which backend to use
BACKEND = os.getenv("MEMORY_BACKEND", "sqlite").lower()

if BACKEND == "sqlite" and HAS_SQL:
    backend_module = memory_sql
    ACTIVE_BACKEND = "sqlite"
elif HAS_JSON:
    ACTIVE_BACKEND = "json"
    backend_module = None
else:
    raise RuntimeError("No memory backend available (JSON or SQLite)")

print(f"[memory] Using {ACTIVE_BACKEND.upper()} backend")


# Initialize backend
if ACTIVE_BACKEND == "sqlite":
    memory_sql.init_memory_db()


# Unified interface
def get_history(conversation_id: str) -> List[Dict[str, Any]]:
    """Get all messages for a conversation."""
    if ACTIVE_BACKEND == "sqlite":
        return memory_sql.get_history(conversation_id)
    else:
        db = _read_json_db()
        return db.get(conversation_id, [])


def save_message_pair(conversation_id: str, user_message: str, ai_message: str) -> None:
    """Save a user/assistant message pair."""
    if ACTIVE_BACKEND == "sqlite":
        memory_sql.save_message_pair(conversation_id, user_message, ai_message)
    else:
        db = _read_json_db()
        now = datetime.utcnow().isoformat() + "Z"
        entry_user = {"role": "user", "message": user_message, "timestamp": now}
        entry_ai = {"role": "assistant", "message": ai_message, "timestamp": now}
        conv = db.get(conversation_id, [])
        conv.append(entry_user)
        conv.append(entry_ai)
        db[conversation_id] = conv
        _write_json_db(db)


def save_memory_entry(
    user_id: str,
    entry: str,
    conversation_id: Optional[str] = None,
    importance: int = 1,
    ttl_days: int = 30
) -> int:
    """Save a memory entry for future reference."""
    if ACTIVE_BACKEND == "sqlite":
        return memory_sql.save_memory_entry(user_id, entry, conversation_id, importance, ttl_days)
    else:
        # JSON backend doesn't support memory entries, return dummy ID
        return -1


def get_user_memory(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get user's memory entries."""
    if ACTIVE_BACKEND == "sqlite":
        return memory_sql.get_user_memory(user_id, limit)
    else:
        # JSON backend doesn't support user memory
        return []


def clear_conversation(conversation_id: str) -> None:
    """Delete all messages in a conversation."""
    if ACTIVE_BACKEND == "sqlite":
        memory_sql.clear_conversation(conversation_id)
    else:
        db = _read_json_db()
        if conversation_id in db:
            del db[conversation_id]
        _write_json_db(db)


def list_conversations(user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """List conversations."""
    if ACTIVE_BACKEND == "sqlite":
        return memory_sql.list_conversations(user_id, limit)
    else:
        db = _read_json_db()
        return [
            {"conversation_id": conv_id, "message_count": len(messages)}
            for conv_id, messages in list(db.items())[:limit]
        ]


def cleanup_expired_memory() -> int:
    """Clean up expired memory entries."""
    if ACTIVE_BACKEND == "sqlite":
        return memory_sql.cleanup_expired_memory()
    else:
        return 0  # JSON backend doesn't support expiration


# Legacy aliases for backward compatibility
def get_conversation_history(conversation_id: str) -> List[Dict[str, Any]]:
    """Alias for get_history (legacy)."""
    return get_history(conversation_id)


if __name__ == "__main__":
    print(f"Memory system initialized with {ACTIVE_BACKEND.upper()} backend")
