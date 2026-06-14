"""
Astravox AI Memory System - SQLite Backend
Manages conversation history and short-term memory with SQLite.
"""

import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")
LOCK = threading.Lock()
MEMORY_RETENTION_DAYS = 30  # Keep memory for 30 days


def _get_conn() -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables() -> None:
    """Create necessary tables if they don't exist."""
    conn = _get_conn()
    cur = conn.cursor()
    
    # Conversations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            user_id TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,  -- 'user' or 'assistant'
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
        )
    """)
    
    # Memory entries table (short-term memory)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            conversation_id TEXT,
            entry TEXT NOT NULL,
            importance INTEGER DEFAULT 1,  -- 1-5 scale
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
        )
    """)
    
    # Create indices for performance
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user 
        ON conversations(user_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_conv 
        ON messages(conversation_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_user 
        ON memory_entries(user_id)
    """)
    
    conn.commit()
    conn.close()


def init_memory_db() -> None:
    """Initialize memory database."""
    with LOCK:
        _ensure_tables()
    print(f"[memory] SQLite memory database initialized at {DB_PATH}")


def get_history(conversation_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a conversation.
    
    Args:
        conversation_id: Unique conversation identifier
    
    Returns:
        List of message dicts with keys: {role, message, timestamp}
    """
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT role, message, timestamp 
            FROM messages 
            WHERE conversation_id = ? 
            ORDER BY timestamp ASC
        """, (conversation_id,))
        rows = cur.fetchall()
        conn.close()
        
        return [
            {
                "role": row["role"],
                "message": row["message"],
                "timestamp": row["timestamp"]
            }
            for row in rows
        ]


def save_message_pair(conversation_id: str, user_message: str, ai_message: str) -> None:
    """
    Save a user/assistant message pair to conversation history.
    
    Args:
        conversation_id: Unique conversation identifier
        user_message: User's message
        ai_message: AI's response
    """
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        
        # Ensure conversation exists
        cur.execute("""
            INSERT OR IGNORE INTO conversations (conversation_id, created_at, last_updated)
            VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (conversation_id,))
        
        # Save messages
        now = datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO messages (conversation_id, role, message, timestamp)
            VALUES (?, 'user', ?, ?)
        """, (conversation_id, user_message, now))
        
        cur.execute("""
            INSERT INTO messages (conversation_id, role, message, timestamp)
            VALUES (?, 'assistant', ?, ?)
        """, (conversation_id, ai_message, now))
        
        # Update conversation last_updated
        cur.execute("""
            UPDATE conversations SET last_updated = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        conn.commit()
        conn.close()


def save_memory_entry(
    user_id: str,
    entry: str,
    conversation_id: Optional[str] = None,
    importance: int = 1,
    ttl_days: int = MEMORY_RETENTION_DAYS
) -> int:
    """
    Save a memory entry for future reference.
    
    Args:
        user_id: User identifier
        entry: Memory entry text
        conversation_id: Optional conversation reference
        importance: 1-5 importance scale
        ttl_days: Days until entry expires
    
    Returns:
        Memory entry ID
    """
    importance = max(1, min(5, importance))  # Clamp 1-5
    
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        cur.execute("""
            INSERT INTO memory_entries 
            (user_id, conversation_id, entry, importance, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, conversation_id, entry, importance, expires_at.isoformat()))
        
        memory_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        return memory_id


def get_user_memory(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get user's memory entries (most recent, non-expired).
    
    Args:
        user_id: User identifier
        limit: Maximum entries to return
    
    Returns:
        List of memory entries
    """
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        cur.execute("""
            SELECT id, entry, importance, created_at, expires_at
            FROM memory_entries
            WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """, (user_id, now, limit))
        
        rows = cur.fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "entry": row["entry"],
                "importance": row["importance"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"]
            }
            for row in rows
        ]


def clear_conversation(conversation_id: str) -> None:
    """Delete all messages in a conversation."""
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
        conn.commit()
        conn.close()


def list_conversations(user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    List conversations, optionally filtered by user.
    
    Args:
        user_id: Optional user filter
        limit: Maximum results
    
    Returns:
        List of conversation dicts
    """
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        
        if user_id:
            cur.execute("""
                SELECT conversation_id, user_id, title, created_at, last_updated
                FROM conversations
                WHERE user_id = ?
                ORDER BY last_updated DESC
                LIMIT ?
            """, (user_id, limit))
        else:
            cur.execute("""
                SELECT conversation_id, user_id, title, created_at, last_updated
                FROM conversations
                ORDER BY last_updated DESC
                LIMIT ?
            """, (limit,))
        
        rows = cur.fetchall()
        conn.close()
        
        return [
            {
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "last_updated": row["last_updated"]
            }
            for row in rows
        ]


def cleanup_expired_memory() -> int:
    """
    Delete expired memory entries.
    
    Returns:
        Number of entries deleted
    """
    with LOCK:
        conn = _get_conn()
        cur = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        cur.execute("""
            DELETE FROM memory_entries
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (now,))
        
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        
        return deleted


if __name__ == "__main__":
    init_memory_db()
    print(f"Memory database at: {DB_PATH}")
