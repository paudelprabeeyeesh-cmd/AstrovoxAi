import base64
import json
import uuid
from datetime import datetime

from .core.encryption import decrypt, encrypt
from .database import get_db
from .schemas import ToolCreate, ToolOut


def create_tool(user_id: str, data: ToolCreate) -> ToolOut:
    tool_id = str(uuid.uuid4())
    config = data.config
    if data.type == "gmail":
        try:
            creds = json.loads(data.config)
            creds["token"] = base64.b64encode(creds.get("token", "").encode()).decode()
            config = json.dumps(creds)
        except Exception:
            pass
    encrypted_config = encrypt(config)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tools (id, user_id, type, config) VALUES (?, ?, ?, ?)",
            (tool_id, user_id, data.type, encrypted_config),
        )
        conn.commit()
    return ToolOut(
        id=tool_id, type=data.type, config=config, created_at=datetime.utcnow()
    )


def get_tool(tool_id: str, user_id: str) -> ToolOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, type, config, created_at FROM tools WHERE id = ? AND user_id = ?",
            (tool_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Tool not found")
        config = decrypt(row["config"])
        if row["type"] == "gmail":
            try:
                creds = json.loads(config)
                creds["token"] = base64.b64decode(creds["token"]).decode()
                config = json.dumps(creds)
            except Exception:
                pass
        return ToolOut(
            id=row["id"],
            type=row["type"],
            config=config,
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_tools(user_id: str) -> list[ToolOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, type, config, created_at FROM tools WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            config = decrypt(r["config"])
            if r["type"] == "gmail":
                try:
                    creds = json.loads(config)
                    creds["token"] = base64.b64decode(creds["token"]).decode()
                    config = json.dumps(creds)
                except Exception:
                    pass
            result.append(
                ToolOut(
                    id=r["id"],
                    type=r["type"],
                    config=config,
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
            )
        return result


def delete_tool(tool_id: str, user_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM tools WHERE id = ? AND user_id = ?", (tool_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError("Tool not found")
