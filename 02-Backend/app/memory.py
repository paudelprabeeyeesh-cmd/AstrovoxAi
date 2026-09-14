import uuid
from datetime import datetime

from .database import get_db
from .schemas import MemoryCreate, MemoryOut, MemoryUpdate


def create_memory(user_id: str, data: MemoryCreate) -> MemoryOut:
    memory_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO memories (id, user_id, key, value) VALUES (?, ?, ?, ?)",
            (memory_id, user_id, data.key, data.value),
        )
        conn.commit()
    return get_memory(memory_id)


def get_memory(memory_id: str) -> MemoryOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if not row:
            raise ValueError("Memory not found")
        return MemoryOut(
            id=row["id"],
            key=row["key"],
            value=row["value"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_memories(user_id: str, limit: int = 100) -> list[MemoryOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            MemoryOut(
                id=r["id"],
                key=r["key"],
                value=r["value"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def update_memory(memory_id: str, user_id: str, data: MemoryUpdate) -> MemoryOut:
    with get_db() as conn:
        conn.execute(
            "UPDATE memories SET value = ? WHERE id = ? AND user_id = ?",
            (data.value, memory_id, user_id),
        )
        conn.commit()
    return get_memory(memory_id)


def delete_memory(memory_id: str, user_id: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id)
        )
        conn.commit()


def search_memories(user_id: str, query: str, limit: int = 5) -> list[MemoryOut]:
    query_lower = query.lower()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE user_id = ? AND (key LIKE ? OR value LIKE ?) ORDER BY created_at DESC LIMIT ?",
            (user_id, f"%{query_lower}%", f"%{query_lower}%", limit),
        ).fetchall()
        return [
            MemoryOut(
                id=r["id"],
                key=r["key"],
                value=r["value"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def export_memories(user_id: str) -> dict:
    memories = list_memories(user_id)
    return {
        "user_id": user_id,
        "exported_at": datetime.utcnow().isoformat(),
        "memories": [m.dict() for m in memories],
    }
