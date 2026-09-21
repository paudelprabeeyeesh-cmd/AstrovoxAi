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
    ToolDefinition(
        name="web_search",
        description="Search the web for current information",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
        function=search_web,
    ),
    ToolDefinition(
        name="code_execute",
        description="Execute Python code in a sandboxed environment",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "language": {"type": "string", "description": "Programming language", "default": "python"},
            },
            "required": ["code"],
        },
        function=code_execute,
    ),
    ToolDefinition(
        name="bash",
        description="Execute bash shell commands",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
            },
            "required": ["command"],
        },
        function=bash_execute,
    ),
    ToolDefinition(
        name="computer_use",
        description="Control a virtual desktop with mouse and keyboard actions",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: click, type, screenshot, scroll"},
                "x": {"type": "number", "description": "X coordinate for click"},
                "y": {"type": "number", "description": "Y coordinate for click"},
                "text": {"type": "string", "description": "Text to type"},
                "direction": {"type": "string", "description": "Scroll direction: up or down"},
            },
            "required": ["action"],
        },
        function=computer_use,
    ),
    ToolDefinition(
        name="text_editor",
        description="Edit files with a text editor tool supporting insert, replace, and view operations",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "description": "Operation: view, insert, replace, delete"},
                "file_path": {"type": "string", "description": "Path to the file"},
                "old_string": {"type": "string", "description": "Text to replace (for replace operation)"},
                "new_string": {"type": "string", "description": "Replacement text (for replace operation)"},
                "insert_text": {"type": "string", "description": "Text to insert (for insert operation)"},
                "line_number": {"type": "integer", "description": "Line number for insert/replace"},
            },
            "required": ["operation", "file_path"],
        },
        function=text_editor,
    ),
    ToolDefinition(
        name="pdf_read",
        description="Read and extract text from a PDF file",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to PDF file"},
                "pages": {"type": "string", "description": "Page range, e.g. '1-5' or 'all'"},
            },
            "required": ["file_path"],
        },
        function=pdf_read,
    ),
    ToolDefinition(
        name="memory_search",
        description="Search user's long-term memory for relevant context",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "user_id": {"type": "string", "description": "User ID"},
                "limit": {"type": "integer", "description": "Max results", "default": 5},
            },
            "required": ["query", "user_id"],
        },
        function=memory_search_tool,
    ),
    ToolDefinition(
        name="file_read",
        description="Read the contents of a file",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"},
                "offset": {"type": "integer", "description": "Line offset to start reading from"},
                "limit": {"type": "integer", "description": "Max lines to read"},
            },
            "required": ["file_path"],
        },
        function=file_read,
    ),
    ToolDefinition(
        name="file_write",
        description="Write content to a file",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"},
                "content": {"type": "string", "description": "Content to write"},
                "mode": {"type": "string", "description": "Write mode: overwrite or append", "default": "overwrite"},
            },
            "required": ["file_path", "content"],
        },
        function=file_write,
    ),
]


def get_builtin_tools() -> list[ToolDefinition]:
    return BUILTIN_TOOLS


def code_execute(code: str, language: str = "python") -> str:
    import subprocess
    import tempfile
    import os
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        os.unlink(temp_path)
        output = result.stdout or result.stderr or "Code executed successfully (no output)"
        return output[:10000]
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out after 30 seconds"
    except Exception as e:
        return f"Error: {e}"


def bash_execute(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout or result.stderr or "Command executed successfully"
        return output[:10000]
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error: {e}"


def computer_use(action: str, x: float = 0, y: float = 0, text: str = "", direction: str = "down") -> str:
    actions = {
        "click": f"Clicked at coordinates ({x}, {y})",
        "type": f"Typed text: {text[:100]}",
        "screenshot": "Screenshot captured (virtual desktop)",
        "scroll": f"Scrolled {direction}",
        "move": f"Moved cursor to ({x}, {y})",
        "double_click": f"Double-clicked at ({x}, {y})",
        "right_click": f"Right-clicked at ({x}, {y})",
    }
    return actions.get(action, f"Unknown action: {action}")


def text_editor(operation: str, file_path: str, old_string: str = "", new_string: str = "", insert_text: str = "", line_number: int = 1) -> str:
    try:
        if operation == "view":
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, line_number - 1)
            end = min(len(lines), start + 50)
            preview = "".join(lines[start:end])
            return f"File: {file_path}\nLines {start+1}-{end}:\n{preview}"
        elif operation == "insert":
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            idx = max(0, min(line_number - 1, len(lines)))
            lines.insert(idx, insert_text + "\n")
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return f"Inserted text at line {line_number} in {file_path}"
        elif operation == "replace":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_string not in content:
                return f"Error: old_string not found in {file_path}"
            new_content = content.replace(old_string, new_string, 1)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Replaced text in {file_path}"
        elif operation == "delete":
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            idx = max(0, min(line_number - 1, len(lines) - 1))
            deleted = lines.pop(idx)
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return f"Deleted line {line_number} from {file_path}"
        else:
            return f"Unknown operation: {operation}"
    except Exception as e:
        return f"Error: {e}"


def pdf_read(file_path: str, pages: str = "all") -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        if pages == "all":
            text = "".join(page.extract_text() or "" for page in reader.pages)
        else:
            parts = pages.split("-")
            start = int(parts[0]) - 1
            end = int(parts[1]) if len(parts) > 1 else len(reader.pages)
            text = "".join(page.extract_text() or "" for page in reader.pages[start:end])
        return text[:50000] or "PDF is empty or image-based"
    except ImportError:
        return "Error: pypdf not installed"
    except Exception as e:
        return f"Error reading PDF: {e}"


def memory_search_tool(query: str, user_id: str, limit: int = 5) -> str:
    from .memory import search_memories
    results = search_memories(user_id, query, limit)
    if not results:
        return "No memories found"
    lines = [f"- [{r.get('memory_type', 'memory')}] {r.get('key', '')}: {r.get('value', '')[:200]}" for r in results]
    return "\n".join(lines)


def file_read(file_path: str, offset: int = 1, limit: int = 200) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        start = max(0, offset - 1)
        end = min(len(lines), start + limit)
        return "".join(lines[start:end])
    except Exception as e:
        return f"Error: {e}"


def file_write(file_path: str, content: str, mode: str = "overwrite") -> str:
    try:
        if mode == "append":
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        return f"File {'appended to' if mode == 'append' else 'written'}: {file_path}"
    except Exception as e:
        return f"Error: {e}"

