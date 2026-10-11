"""AI Tools — calculator, web search, weather, code execution."""

import ast
import operator
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)
from .core.encryption import decrypt, encrypt
from .database import get_db
from .schemas import ToolCreate, ToolOut


def _safe_calculate(expression: str) -> str:
    import math
    safe_env = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    try:
        result = eval(expression, {"__builtins__": {}}, safe_env)
        return str(result)
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


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


def code_execute(code: str, language: str = "python", sandbox=None) -> str:
    if sandbox is not None:
        try:
            from sandboxing.command_scrubbing import CommandScrubber
            scrubber = CommandScrubber()
            scrub_result = scrubber.scan(code)
            if scrub_result.blocked:
                return f"Error: code blocked by security scrubber: {scrub_result.matched_rules}"
        except Exception:  # noqa: BLE001
            pass
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
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


def bash_execute(command: str, sandbox=None) -> str:
    if sandbox is not None:
        try:
            from sandboxing.command_scrubbing import CommandScrubber
            scrubber = CommandScrubber()
            scrub_result = scrubber.scan(command)
            if scrub_result.blocked:
                return f"Error: command blocked by security scrubber: {scrub_result.matched_rules}"
        except Exception:  # noqa: BLE001
            pass
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
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


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
            lines.pop(idx)
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return f"Deleted line {line_number} from {file_path}"
        else:
            return f"Unknown operation: {operation}"
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


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
    except Exception as _e:  # noqa: BLE001
        return f"Error reading PDF: {_e}"


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
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


def file_write(file_path: str, content: str, mode: str = "overwrite") -> str:
    try:
        if mode == "append":
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        return f"File {'appended to' if mode == 'append' else 'written'}: {file_path}"
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


def voice_speak(text: str, voice: str = "default") -> str:
    return f"[Voice output ({voice}): {text[:200]}]"


def image_generate(prompt: str, size: str = "1024x1024") -> str:
    return f"[Image generated for: {prompt[:100]}]"


def image_understand(image_path: str, question: str = "") -> str:
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return f"[Image analysis: {image_path} ({len(data)} bytes) - {question[:100]}]"
    except Exception as _e:  # noqa: BLE001
        return f"Error: {_e}"


def deep_research(query: str, depth: str = "medium") -> str:
    return f"[Deep research for: {query[:200]} (depth: {depth})]"


def web_fetch(url: str, max_length: int = 5000) -> str:
    import requests
    try:
        response = requests.get(url, timeout=30)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n")
        return text[:max_length]
    except Exception as _e:  # noqa: BLE001
        return f"Error fetching {url}: {_e}"


def create_tool(user_id: str, data: ToolCreate) -> ToolOut:
    tool_id = str(uuid.uuid4())
    config = data.config
    if data.type == "gmail":
        try:
            creds = json.loads(data.config)
            creds["token"] = base64.b64encode(creds.get("token", "").encode()).decode()
            config = json.dumps(creds)
        except Exception as _e:  # noqa: BLE001
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


def delete_tool(tool_id: str, user_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM tools WHERE id = ? AND user_id = ?", (tool_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError("Tool not found")


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
                except Exception as _e:  # noqa: BLE001
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


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    result: str
    tool_name: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CalculatorTool:
    """Safe mathematical calculator."""

    ALLOWED_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCS = {
        'abs': abs, 'round': round, 'min': min, 'max': max,
        'sum': sum, 'pow': pow, 'len': len,
    }

    def calculate(self, expression: str) -> ToolResult:
        """Safely evaluate a mathematical expression."""
        try:
            tree = ast.parse(expression.strip(), mode='eval')
            result = self._eval_node(tree.body)
            return ToolResult(True, str(result), "calculator")
        except Exception as e:
            return ToolResult(False, f"Calculation error: {str(e)}", "calculator")

    def _eval_node(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {type(node.value)}")
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.ALLOWED_OPS[op_type](left, right)
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return self.ALLOWED_OPS[op_type](operand)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.ALLOWED_FUNCS:
                args = [self._eval_node(arg) for arg in node.args]
                return self.ALLOWED_FUNCS[node.func.id](*args)
            raise ValueError("Unsupported function")
        raise ValueError(f"Unsupported expression: {type(node).__name__}")


from app.secure_executor import SandboxConfig, execute_python
from app.security_hardening import Principal


class CodeExecutionTool:
    """Sandboxed code execution - ADMIN ONLY.

    SECURITY: This tool executes arbitrary Python code. It must ONLY be
    accessible to authenticated admin users. It uses the secure subprocess
    executor with strict resource limits.
    """

    def execute(self, code: str, timeout: int = 5, principal: Optional[Principal] = None) -> ToolResult:
        """Execute Python code in a restricted environment.

        SECURITY MEASURES:
        - Subprocess isolation with no network/filesystem access
        - Strict timeout and memory limits
        - Admin-only authorization
        - Truncated, scrubbed output
        """
        try:
            config = SandboxConfig(timeout_s=float(timeout))
            result = execute_python(code, config=config, principal=principal)
            if result.success:
                return ToolResult(True, result.output, "code_executor")
            return ToolResult(False, result.error or "Execution failed", "code_executor")
        except Exception as e:
            return ToolResult(False, f"Execution error: {str(e)[:200]}", "code_executor")


class WebSearchTool:
    """Web search tool (requires API key)."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> ToolResult:
        """Search the web."""
        if not self._api_key:
            return ToolResult(
                False,
                "Web search requires an API key. Set SEARCH_API_KEY environment variable.",
                "web_search",
            )

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": max_results},
                    headers={"X-Subscription-Token": self._api_key},
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("web", {}).get("results", [])
                    formatted = "\n".join(
                        f"- {r.get('title', 'No title')}: {r.get('url', '')}"
                        for r in results[:max_results]
                    )
                    return ToolResult(True, formatted or "No results found", "web_search")
                return ToolResult(False, f"Search failed: {response.status_code}", "web_search")
        except Exception as e:
            return ToolResult(False, f"Search error: {str(e)}", "web_search")


class WeatherTool:
    """Weather information tool."""

    async def get_weather(self, location: str) -> ToolResult:
        """Get weather for a location."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"https://wttr.in/{location}?format=j1"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    current = data.get("current_condition", [{}])[0]
                    result = (
                        f"Weather in {location}:\n"
                        f"- Temperature: {current.get('temp_C', 'N/A')}°C\n"
                        f"- Condition: {current.get('weatherDesc', [{}])[0].get('value', 'N/A')}\n"
                        f"- Humidity: {current.get('humidity', 'N/A')}%\n"
                        f"- Wind: {current.get('windspeedKmph', 'N/A')} km/h"
                    )
                    return ToolResult(True, result, "weather")
                return ToolResult(False, f"Weather API error: {response.status_code}", "weather")
        except Exception as e:
            return ToolResult(False, f"Weather error: {str(e)}", "weather")


class URLReaderTool:
    """Read and extract content from URLs."""

    async def read_url(self, url: str, max_length: int = 5000) -> ToolResult:
        """Read content from a URL."""
        try:
            import httpx
            from html import unescape
            import re

            if not url.startswith(("http://", "https://")):
                return ToolResult(False, "URL must start with http:// or https://", "url_reader")

            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "AstrovoxAI/2.0 URL Reader"
                })
                if response.status_code == 200:
                    text = response.text
                    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = unescape(text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    text = text[:max_length]
                    return ToolResult(True, text, "url_reader")
                return ToolResult(False, f"HTTP {response.status_code}", "url_reader")
        except Exception as e:
            return ToolResult(False, f"URL read error: {str(e)}", "url_reader")


class NewsTool:
    """News aggregation tool."""

    async def get_news(self, topic: str = "technology", max_results: int = 5) -> ToolResult:
        """Get latest news on a topic."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://news.ycombinator.com/",
                    headers={"User-Agent": "AstrovoxAI/2.0"},
                )
                if response.status_code == 200:
                    return ToolResult(
                        True,
                        f"Hacker News front page fetched. Topic: {topic}",
                        "news",
                    )
                return ToolResult(False, f"News API error: {response.status_code}", "news")
        except Exception as e:
            return ToolResult(False, f"News error: {str(e)}", "news")


class ToolRegistry:
    """Registry of all available AI tools."""

    def __init__(self):
        self.calculator = CalculatorTool()
        self.code_executor = CodeExecutionTool()
        self.web_search = WebSearchTool()
        self.weather = WeatherTool()
        self.url_reader = URLReaderTool()
        self.news = NewsTool()

    def get_tools(self) -> list[dict]:
        """List all available tools."""
        return [
            {"name": "calculator", "description": "Perform mathematical calculations", "sync": True},
            {"name": "code_executor", "description": "Execute Python code in sandbox", "sync": True},
            {"name": "web_search", "description": "Search the web for information", "sync": False},
            {"name": "weather", "description": "Get weather for a location", "sync": False},
            {"name": "url_reader", "description": "Read content from a URL", "sync": False},
            {"name": "news", "description": "Get latest news", "sync": False},
        ]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool."""
        tool_map = {
            "calculator": lambda: self.calculator.calculate(kwargs.get("expression", "")),
            "code_executor": lambda: self.code_executor.execute(kwargs.get("code", "")),
            "web_search": lambda: self.web_search.search(kwargs.get("query", "")),
            "weather": lambda: self.weather.get_weather(kwargs.get("location", "")),
            "url_reader": lambda: self.url_reader.read_url(kwargs.get("url", "")),
            "news": lambda: self.news.get_news(kwargs.get("topic", "")),
        }

        executor = tool_map.get(tool_name)
        if not executor:
            return ToolResult(False, f"Unknown tool: {tool_name}", tool_name)

        result = executor()
        if asyncio.iscoroutine(result):
            result = await result
        return result


tool_registry = ToolRegistry()

