import base64
import json
import uuid
from datetime import datetime, timezone

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
        id=tool_id, type=data.type, config=config, created_at=datetime.now(timezone.utc)
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

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _safe_calculate(expression: str) -> str:
    import math
    safe_env = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    try:
        result = eval(expression, {"__builtins__": {}}, safe_env)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def search_web(query: str) -> str:
    return f"[web search result for: {query}]"


def calculate(expression: str) -> str:
    return _safe_calculate(expression)


def get_current_time() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def get_weather(location: str) -> str:
    return f"[weather for {location}: 72F, clear]"


def search_documents(query: str, user_id: str) -> str:
    from .knowledge import search_docs
    docs = search_docs(user_id, query, limit=3)
    return "\n".join([d.content[:500] for d in docs]) if docs else "No documents found."


def create_memory(content: str, user_id: str) -> str:
    from .memory import create_memory as _create_memory
    from .schemas import MemoryCreate
    mem = _create_memory(user_id, MemoryCreate(key="tool_memory", value=content))
    return f"Memory created: {mem.id}"


def send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to}: {subject}"


BUILTIN_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="search_web",
        description="Search the web for information",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
        function=search_web,
    ),
    ToolDefinition(
        name="calculate",
        description="Evaluate a mathematical expression",
        parameters={
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "Math expression"}},
            "required": ["expression"],
        },
        function=calculate,
    ),
    ToolDefinition(
        name="get_current_time",
        description="Get the current UTC time",
        parameters={"type": "object", "properties": {}},
        function=get_current_time,
    ),
    ToolDefinition(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
            "type": "object",
            "properties": {"location": {"type": "string", "description": "City name"}},
            "required": ["location"],
        },
        function=get_weather,
    ),
    ToolDefinition(
        name="search_documents",
        description="Search user documents",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "user_id": {"type": "string", "description": "User ID"},
            },
            "required": ["query", "user_id"],
        },
        function=search_documents,
    ),
    ToolDefinition(
        name="create_memory",
        description="Create a memory for the user",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Memory content"},
                "user_id": {"type": "string", "description": "User ID"},
            },
            "required": ["content", "user_id"],
        },
        function=create_memory,
    ),
    ToolDefinition(
        name="send_email",
        description="Send an email",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
            },
            "required": ["to", "subject", "body"],
        },
        function=send_email,
    ),
]


def get_builtin_tools() -> list[ToolDefinition]:
    return BUILTIN_TOOLS
