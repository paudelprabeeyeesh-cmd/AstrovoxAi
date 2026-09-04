"""AI Tools — calculator, web search, weather, code execution."""

import re
import ast
import operator
import logging
import asyncio
import json
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
