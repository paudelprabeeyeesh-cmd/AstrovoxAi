"""Tools package for AI agent tools."""

import ast
import operator
import logging
import asyncio
import json
import re
import os
import io
import base64
import subprocess
import sys
import tempfile
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .registry import ToolRegistry, ToolDefinition, ToolCategory
from .executor import ToolExecutor, ToolResult as ExecutorToolResult
from .sandbox import ToolSandbox, SandboxPolicy, SandboxMode
from .permissions import ToolPermissionManager, ToolAccessPolicy, ToolPermission
from .schema_validator import SchemaValidator as ToolSchemaValidator
from .function_calling import FunctionCallingFramework, ToolCall, ToolDefinition as FCToolDefinition
from .caching import ToolCache
from .rate_limits import ToolRateLimiter
from .custom_builder import CustomToolBuilder as ToolBuilder

logger = logging.getLogger(__name__)


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class ToolResult:
    success: bool
    result: str
    tool_name: str
    error: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============================================================================
# Calculator Tool
# ============================================================================


class CalculatorTool:
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


# ============================================================================
# Weather Tool
# ============================================================================


class WeatherTool:
    async def get_weather(self, location: str) -> ToolResult:
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


# ============================================================================
# Web Search Tool
# ============================================================================


class WebSearchTool:
    def __init__(self, api_key: str = ""):
        self._api_key = api_key or os.getenv("SEARCH_API_KEY", "")

    async def search(self, query: str, max_results: int = 5) -> ToolResult:
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


# ============================================================================
# Code Execution Tool
# ============================================================================


class CodeExecutionTool:
    def execute(self, code: str, timeout: int = 5, principal: Optional[Any] = None) -> ToolResult:
        try:
            from app.secure_executor import SandboxConfig, execute_python
            config = SandboxConfig(timeout_s=float(timeout))
            result = execute_python(code, config=config, principal=principal)
            if result.success:
                return ToolResult(True, result.output, "code_executor")
            return ToolResult(False, result.error or "Execution failed", "code_executor")
        except Exception as e:
            return ToolResult(False, f"Execution error: {str(e)[:200]}", "code_executor")


# ============================================================================
# Terminal Tool
# ============================================================================


class TerminalTool:
    BLOCKED_COMMANDS = {"rm", "sudo", "su", "chmod", "chown", "kill", "pkill", "shutdown", "reboot", "curl", "wget", "nc", "netcat", "nmap"}

    async def execute(self, command: str, timeout: int = 10) -> ToolResult:
        try:
            cmd_parts = command.strip().split()
            if cmd_parts and cmd_parts[0].lower() in self.BLOCKED_COMMANDS:
                return ToolResult(False, f"Blocked command: {cmd_parts[0]}", "terminal")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )
            output = result.stdout[:50000]
            if result.stderr:
                output += "\n" + result.stderr[:50000]
            if result.returncode != 0:
                return ToolResult(False, output or "Command failed", "terminal")
            return ToolResult(True, output, "terminal")
        except subprocess.TimeoutExpired:
            return ToolResult(False, f"Command timed out after {timeout}s", "terminal")
        except Exception as e:
            return ToolResult(False, f"Terminal error: {str(e)}", "terminal")


# ============================================================================
# Python Sandbox Tool
# ============================================================================


class PythonSandboxTool:
    BLOCKED_MODULES = {"subprocess", "socket", "requests", "urllib", "http", "ftplib", "smtplib", "ctypes", "multiprocessing", "threading", "asyncio"}

    def execute(self, code: str, timeout: int = 5) -> ToolResult:
        try:
            import ast as pyast
            tree = pyast.parse(code)
            for node in pyast.walk(tree):
                if isinstance(node, (pyast.Import, pyast.ImportFrom)):
                    names = [alias.name for alias in getattr(node, 'names', [])]
                    for name in names:
                        if name in self.BLOCKED_MODULES:
                            return ToolResult(False, f"Blocked module: {name}", "python_sandbox")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                temp_path = f.name
            try:
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tempfile.gettempdir(),
                )
                output = result.stdout[:100000]
                if result.stderr:
                    output += "\n" + result.stderr[:100000]
                if result.returncode != 0:
                    return ToolResult(False, output or "Execution failed", "python_sandbox")
                return ToolResult(True, output, "python_sandbox")
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
        except SyntaxError as e:
            return ToolResult(False, f"Syntax error: {e}", "python_sandbox")
        except Exception as e:
            return ToolResult(False, f"Sandbox error: {str(e)}", "python_sandbox")


# ============================================================================
# SQL Execution Tool
# ============================================================================


class SQLExecutionTool:
    def __init__(self, database_url: str = ""):
        self._database_url = database_url or os.getenv("DATABASE_URL", "")

    def execute(self, query: str, read_only: bool = True) -> ToolResult:
        if not self._database_url:
            return ToolResult(False, "Database URL not configured. Set DATABASE_URL.", "sql_executor")
        try:
            forbidden = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"}
            if read_only:
                query_upper = query.strip().upper()
                for cmd in forbidden:
                    if query_upper.startswith(cmd):
                        return ToolResult(False, f"Read-only mode blocks: {cmd}", "sql_executor")
            from sqlalchemy import create_engine, text
            engine = create_engine(self._database_url, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = list(result.keys())
                    formatted = "\n".join([" | ".join(columns)] + [" | ".join(str(v) for v in row) for row in rows[:100]])
                    return ToolResult(True, formatted, "sql_executor")
                conn.commit()
                return ToolResult(True, f"Query executed. Rows affected: {result.rowcount}", "sql_executor")
        except Exception as e:
            return ToolResult(False, f"SQL error: {str(e)}", "sql_executor")


# ============================================================================
# Browser Automation Tool
# ============================================================================


class BrowserAutomationTool:
    async def navigate(self, url: str) -> ToolResult:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=15000)
                title = await page.title()
                content = await page.content()
                text = await page.inner_text("body")
                await browser.close()
                return ToolResult(True, f"Title: {title}\n\nContent preview:\n{text[:2000]}", "browser")
        except Exception as e:
            return ToolResult(False, f"Browser error: {str(e)}", "browser")

    async def screenshot(self, url: str, output_path: str = "") -> ToolResult:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=15000)
                path = output_path or tempfile.mktemp(suffix=".png")
                await page.screenshot(path=path)
                await browser.close()
                return ToolResult(True, f"Screenshot saved to {path}", "browser")
        except Exception as e:
            return ToolResult(False, f"Screenshot error: {str(e)}", "browser")


# ============================================================================
# Calendar Tool
# ============================================================================


class CalendarTool:
    async def list_events(self, start_time: str = "", end_time: str = "") -> ToolResult:
        try:
            import httpx
            token = os.getenv("GOOGLE_CALENDAR_TOKEN", "")
            if not token:
                return ToolResult(False, "Google Calendar token not configured.", "calendar")
            async with httpx.AsyncClient(timeout=10) as client:
                params = {"timeMin": start_time, "timeMax": end_time, "singleEvents": True}
                resp = await client.get(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if resp.status_code == 200:
                    events = resp.json().get("items", [])
                    if not events:
                        return ToolResult(True, "No upcoming events found.", "calendar")
                    lines = [f"{e.get('summary', 'No title')} ({e.get('start', {}).get('dateTime', e.get('start', {}).get('date', ''))})" for e in events[:10]]
                    return ToolResult(True, "\n".join(lines), "calendar")
                return ToolResult(False, f"Calendar API error: {resp.status_code}", "calendar")
        except Exception as e:
            return ToolResult(False, f"Calendar error: {str(e)}", "calendar")

    async def create_event(self, title: str, start_time: str, end_time: str, description: str = "") -> ToolResult:
        try:
            import httpx
            token = os.getenv("GOOGLE_CALENDAR_TOKEN", "")
            if not token:
                return ToolResult(False, "Google Calendar token not configured.", "calendar")
            event = {"summary": title, "description": description, "start": {"dateTime": start_time}, "end": {"dateTime": end_time}}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=event,
                )
                if resp.status_code in (200, 201):
                    return ToolResult(True, f"Event created: {resp.json().get('htmlLink', '')}", "calendar")
                return ToolResult(False, f"Calendar API error: {resp.status_code}", "calendar")
        except Exception as e:
            return ToolResult(False, f"Calendar error: {str(e)}", "calendar")


# ============================================================================
# Email Tool
# ============================================================================


class EmailTool:
    async def send(self, to: str, subject: str, body: str, from_email: str = "") -> ToolResult:
        try:
            sendgrid_key = os.getenv("SENDGRID_API_KEY", "")
            if sendgrid_key:
                import httpx
                data = {
                    "personalizations": [{"to": [{"email": to}], "subject": subject}],
                    "from": {"email": from_email or os.getenv("DEFAULT_FROM_EMAIL", "noreply@astrovox.ai")},
                    "content": [{"type": "text/plain", "value": body}],
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
                        json=data,
                    )
                    if resp.status_code in (200, 202):
                        return ToolResult(True, f"Email sent to {to}", "email")
                    return ToolResult(False, f"SendGrid error: {resp.status_code} {resp.text}", "email")
            return ToolResult(False, "Email service not configured. Set SENDGRID_API_KEY.", "email")
        except Exception as e:
            return ToolResult(False, f"Email error: {str(e)}", "email")


# ============================================================================
# Maps Tool
# ============================================================================


class MapsTool:
    async def geocode(self, address: str) -> ToolResult:
        try:
            api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
            if not api_key:
                return ToolResult(False, "Google Maps API key not configured.", "maps")
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={"address": address, "key": api_key},
                )
                data = resp.json()
                if data.get("status") == "OK":
                    loc = data["results"][0]["geometry"]["location"]
                    return ToolResult(True, f"Lat: {loc['lat']}, Lng: {loc['lng']}", "maps")
                return ToolResult(False, f"Geocoding failed: {data.get('status')}", "maps")
        except Exception as e:
            return ToolResult(False, f"Maps error: {str(e)}", "maps")

    async def directions(self, origin: str, destination: str) -> ToolResult:
        try:
            api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
            if not api_key:
                return ToolResult(False, "Google Maps API key not configured.", "maps")
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://maps.googleapis.com/maps/api/directions/json",
                    params={"origin": origin, "destination": destination, "key": api_key},
                )
                data = resp.json()
                if data.get("status") == "OK":
                    route = data["routes"][0]["legs"][0]
                    return ToolResult(True, f"Distance: {route['distance']['text']}, Duration: {route['duration']['text']}", "maps")
                return ToolResult(False, f"Directions failed: {data.get('status')}", "maps")
        except Exception as e:
            return ToolResult(False, f"Maps error: {str(e)}", "maps")


# ============================================================================
# OCR Tool
# ============================================================================


class OCRTool:
    def extract_text(self, image_path: str) -> ToolResult:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return ToolResult(True, text.strip(), "ocr")
        except Exception as e:
            return ToolResult(False, f"OCR error: {str(e)}", "ocr")


# ============================================================================
# Image Generation Tool
# ============================================================================


class ImageGenerationTool:
    async def generate(self, prompt: str, size: str = "1024x1024") -> ToolResult:
        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return ToolResult(False, "OpenAI API key not configured for image generation.", "image_generator")
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    url = data.get("data", [{}])[0].get("url", "")
                    return ToolResult(True, url, "image_generator")
                return ToolResult(False, f"Image generation failed: {resp.status_code} {resp.text}", "image_generator")
        except Exception as e:
            return ToolResult(False, f"Image generation error: {str(e)}", "image_generator")


# ============================================================================
# Image Editing Tool
# ============================================================================


class ImageEditingTool:
    def resize(self, image_path: str, width: int, height: int, output_path: str = "") -> ToolResult:
        try:
            from PIL import Image
            img = Image.open(image_path)
            resized = img.resize((width, height))
            out = output_path or image_path
            resized.save(out)
            return ToolResult(True, f"Image resized to {width}x{height} and saved to {out}", "image_editor")
        except Exception as e:
            return ToolResult(False, f"Image edit error: {str(e)}", "image_editor")

    def crop(self, image_path: str, left: int, top: int, right: int, bottom: int, output_path: str = "") -> ToolResult:
        try:
            from PIL import Image
            img = Image.open(image_path)
            cropped = img.crop((left, top, right, bottom))
            out = output_path or image_path
            cropped.save(out)
            return ToolResult(True, f"Image cropped and saved to {out}", "image_editor")
        except Exception as e:
            return ToolResult(False, f"Image edit error: {str(e)}", "image_editor")

    def rotate(self, image_path: str, degrees: int, output_path: str = "") -> ToolResult:
        try:
            from PIL import Image
            img = Image.open(image_path)
            rotated = img.rotate(degrees, expand=True)
            out = output_path or image_path
            rotated.save(out)
            return ToolResult(True, f"Image rotated {degrees}° and saved to {out}", "image_editor")
        except Exception as e:
            return ToolResult(False, f"Image edit error: {str(e)}", "image_editor")


# ============================================================================
# Video Generation Tool
# ============================================================================


class VideoGenerationTool:
    async def generate_from_text(self, prompt: str, duration_seconds: int = 5) -> ToolResult:
        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return ToolResult(False, "OpenAI API key not configured for video generation.", "video_generator")
            return ToolResult(False, "Video generation requires RunwayML or Pika API integration. Configure RUNWAY_API_KEY.", "video_generator")
        except Exception as e:
            return ToolResult(False, f"Video generation error: {str(e)}", "video_generator")


# ============================================================================
# Audio Editing Tool
# ============================================================================


class AudioEditingTool:
    def trim(self, audio_path: str, start_seconds: float, end_seconds: float, output_path: str = "") -> ToolResult:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            trimmed = audio[start_seconds * 1000:end_seconds * 1000]
            out = output_path or audio_path
            trimmed.export(out, format=out.split(".")[-1] or "mp3")
            return ToolResult(True, f"Audio trimmed and saved to {out}", "audio_editor")
        except Exception as e:
            return ToolResult(False, f"Audio edit error: {str(e)}", "audio_editor")

    def convert(self, audio_path: str, output_format: str = "mp3", output_path: str = "") -> ToolResult:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            out = output_path or f"{os.path.splitext(audio_path)[0]}.{output_format}"
            audio.export(out, format=output_format)
            return ToolResult(True, f"Audio converted to {output_format} and saved to {out}", "audio_editor")
        except Exception as e:
            return ToolResult(False, f"Audio edit error: {str(e)}", "audio_editor")


# ============================================================================
# PDF Analysis Tool
# ============================================================================


class PDFAnalysisTool:
    def extract_text(self, pdf_path: str) -> ToolResult:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            return ToolResult(True, text[:100000], "pdf_analyzer")
        except Exception as e:
            return ToolResult(False, f"PDF error: {str(e)}", "pdf_analyzer")

    def extract_metadata(self, pdf_path: str) -> ToolResult:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                meta = pdf.metadata or {}
                return ToolResult(True, json.dumps(meta, default=str), "pdf_analyzer")
        except Exception as e:
            return ToolResult(False, f"PDF error: {str(e)}", "pdf_analyzer")


# ============================================================================
# CSV Analysis Tool
# ============================================================================


class CSVAnalysisTool:
    def analyze(self, csv_path: str) -> ToolResult:
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            summary = {
                "rows": int(len(df)),
                "columns": int(len(df.columns)),
                "column_names": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
                "numeric_summary": df.describe(include="all").to_dict(),
            }
            return ToolResult(True, json.dumps(summary, default=str), "csv_analyzer")
        except Exception as e:
            return ToolResult(False, f"CSV error: {str(e)}", "csv_analyzer")

    def query(self, csv_path: str, query: str) -> ToolResult:
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            result = df.query(query)
            return ToolResult(True, result.to_string(index=False), "csv_analyzer")
        except Exception as e:
            return ToolResult(False, f"CSV query error: {str(e)}", "csv_analyzer")


# ============================================================================
# GitHub Integration Tool
# ============================================================================


class GitHubIntegrationTool:
    def __init__(self, token: str = ""):
        self._token = token or os.getenv("GITHUB_TOKEN", "")

    async def list_repos(self, username: str = "") -> ToolResult:
        try:
            import httpx
            target = username or os.getenv("GITHUB_USERNAME", "")
            if not target:
                return ToolResult(False, "GitHub username not configured.", "github")
            headers = {"Authorization": f"token {self._token}", "Accept": "application/vnd.github.v3+json"} if self._token else {"Accept": "application/vnd.github.v3+json"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"https://api.github.com/users/{target}/repos", headers=headers)
                if resp.status_code == 200:
                    repos = resp.json()
                    lines = [f"{r['name']} ({r.get('description', 'No description')}) - ⭐ {r.get('stargazers_count', 0)}" for r in repos[:10]]
                    return ToolResult(True, "\n".join(lines), "github")
                return ToolResult(False, f"GitHub API error: {resp.status_code}", "github")
        except Exception as e:
            return ToolResult(False, f"GitHub error: {str(e)}", "github")

    async def create_issue(self, repo: str, title: str, body: str = "") -> ToolResult:
        try:
            if not self._token:
                return ToolResult(False, "GitHub token not configured.", "github")
            import httpx
            headers = {"Authorization": f"token {self._token}", "Accept": "application/vnd.github.v3+json"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://api.github.com/repos/{repo}/issues",
                    headers=headers,
                    json={"title": title, "body": body},
                )
                if resp.status_code in (200, 201):
                    return ToolResult(True, f"Issue created: {resp.json().get('html_url', '')}", "github")
                return ToolResult(False, f"GitHub API error: {resp.status_code}", "github")
        except Exception as e:
            return ToolResult(False, f"GitHub error: {str(e)}", "github")


# ============================================================================
# URL Reader Tool
# ============================================================================


class URLReaderTool:
    async def read_url(self, url: str, max_length: int = 5000) -> ToolResult:
        try:
            import httpx
            from html import unescape
            if not url.startswith(("http://", "https://")):
                return ToolResult(False, "URL must start with http:// or https://", "url_reader")
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "AstrovoxAI/2.0 URL Reader"})
                if response.status_code == 200:
                    text = response.text
                    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = unescape(text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return ToolResult(True, text[:max_length], "url_reader")
                return ToolResult(False, f"HTTP {response.status_code}", "url_reader")
        except Exception as e:
            return ToolResult(False, f"URL read error: {str(e)}", "url_reader")


# ============================================================================
# File Reader Tool
# ============================================================================


class FileReaderTool:
    def read(self, file_path: str) -> ToolResult:
        try:
            if not os.path.exists(file_path):
                return ToolResult(False, f"File not found: {file_path}", "file_reader")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(True, content[:100000], "file_reader")
        except Exception as e:
            return ToolResult(False, f"Error reading file: {str(e)}", "file_reader")


# ============================================================================
# Registry and Singleton
# ============================================================================


class ToolRegistryInstance:
    def __init__(self):
        self.calculator = CalculatorTool()
        self.weather = WeatherTool()
        self.web_search = WebSearchTool()
        self.code_executor = CodeExecutionTool()
        self.terminal = TerminalTool()
        self.python_sandbox = PythonSandboxTool()
        self.sql_executor = SQLExecutionTool()
        self.browser = BrowserAutomationTool()
        self.calendar = CalendarTool()
        self.email = EmailTool()
        self.maps = MapsTool()
        self.ocr = OCRTool()
        self.image_generator = ImageGenerationTool()
        self.image_editor = ImageEditingTool()
        self.video_generator = VideoGenerationTool()
        self.audio_editor = AudioEditingTool()
        self.pdf_analyzer = PDFAnalysisTool()
        self.csv_analyzer = CSVAnalysisTool()
        self.github = GitHubIntegrationTool()
        self.url_reader = URLReaderTool()
        self.file_reader = FileReaderTool()

    def get_tools(self) -> list[dict]:
        return [
            {"name": "calculator", "description": "Perform mathematical calculations", "sync": True},
            {"name": "weather", "description": "Get weather for a location", "sync": False},
            {"name": "web_search", "description": "Search the web for information", "sync": False},
            {"name": "code_executor", "description": "Execute Python code in sandbox", "sync": True},
            {"name": "terminal", "description": "Execute shell commands", "sync": False},
            {"name": "python_sandbox", "description": "Execute Python code in restricted sandbox", "sync": True},
            {"name": "sql_executor", "description": "Execute SQL queries", "sync": True},
            {"name": "browser", "description": "Browser automation and screenshots", "sync": False},
            {"name": "calendar", "description": "Manage calendar events", "sync": False},
            {"name": "email", "description": "Send emails", "sync": False},
            {"name": "maps", "description": "Geocoding and directions", "sync": False},
            {"name": "ocr", "description": "Extract text from images", "sync": True},
            {"name": "image_generator", "description": "Generate images from text", "sync": False},
            {"name": "image_editor", "description": "Edit images (resize, crop, rotate)", "sync": True},
            {"name": "video_generator", "description": "Generate videos from text", "sync": False},
            {"name": "audio_editor", "description": "Edit audio files (trim, convert)", "sync": True},
            {"name": "pdf_analyzer", "description": "Extract text and metadata from PDFs", "sync": True},
            {"name": "csv_analyzer", "description": "Analyze CSV files", "sync": True},
            {"name": "github", "description": "GitHub integration", "sync": False},
            {"name": "url_reader", "description": "Read content from URLs", "sync": False},
            {"name": "file_reader", "description": "Read text files", "sync": True},
        ]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        tool_map = {
            "calculator": lambda: self.calculator.calculate(kwargs.get("expression", "")),
            "weather": lambda: self.weather.get_weather(kwargs.get("location", "")),
            "web_search": lambda: self.web_search.search(kwargs.get("query", "")),
            "code_executor": lambda: self.code_executor.execute(kwargs.get("code", ""), principal=kwargs.get("principal")),
            "terminal": lambda: self.terminal.execute(kwargs.get("command", "")),
            "python_sandbox": lambda: self.python_sandbox.execute(kwargs.get("code", "")),
            "sql_executor": lambda: self.sql_executor.execute(kwargs.get("query", "")),
            "browser": lambda: self.browser.navigate(kwargs.get("url", "")),
            "calendar": lambda: self.calendar.list_events(kwargs.get("start_time", ""), kwargs.get("end_time", "")),
            "email": lambda: self.email.send(kwargs.get("to", ""), kwargs.get("subject", ""), kwargs.get("body", "")),
            "maps": lambda: self.maps.geocode(kwargs.get("address", "")),
            "ocr": lambda: self.ocr.extract_text(kwargs.get("image_path", "")),
            "image_generator": lambda: self.image_generator.generate(kwargs.get("prompt", "")),
            "image_editor": lambda: self.image_editor.resize(kwargs.get("image_path", ""), kwargs.get("width", 0), kwargs.get("height", 0)),
            "video_generator": lambda: self.video_generator.generate_from_text(kwargs.get("prompt", "")),
            "audio_editor": lambda: self.audio_editor.trim(kwargs.get("audio_path", ""), kwargs.get("start_seconds", 0.0), kwargs.get("end_seconds", 0.0)),
            "pdf_analyzer": lambda: self.pdf_analyzer.extract_text(kwargs.get("pdf_path", "")),
            "csv_analyzer": lambda: self.csv_analyzer.analyze(kwargs.get("csv_path", "")),
            "github": lambda: self.github.list_repos(kwargs.get("username", "")),
            "url_reader": lambda: self.url_reader.read_url(kwargs.get("url", "")),
            "file_reader": lambda: self.file_reader.read(kwargs.get("file_path", "")),
        }

        executor = tool_map.get(tool_name)
        if not executor:
            return ToolResult(False, f"Unknown tool: {tool_name}", tool_name)

        result = executor()
        if asyncio.iscoroutine(result):
            result = await result
        return result


tool_registry = ToolRegistryInstance()


# ============================================================================
# Builtin Tools for OpenAI Schema
# ============================================================================


class BuiltinTool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def get_builtin_tools() -> List[BuiltinTool]:
    registry = tool_registry
    return [
        BuiltinTool("calculator", "Perform mathematical calculations", {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "Mathematical expression to evaluate"}},
            "required": ["expression"],
        }, lambda **kw: registry.calculator.calculate(kw.get("expression", ""))),
        BuiltinTool("weather", "Get weather for a location", {
            "type": "object",
            "properties": {"location": {"type": "string", "description": "City or location name"}},
            "required": ["location"],
        }, lambda **kw: registry.weather.get_weather(kw.get("location", ""))),
        BuiltinTool("web_search", "Search the web for information", {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results", "default": 5},
            },
            "required": ["query"],
        }, lambda **kw: registry.web_search.search(kw.get("query", ""), kw.get("num_results", 5))),
        BuiltinTool("code_executor", "Execute Python code in sandbox", {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute"}},
            "required": ["code"],
        }, lambda **kw: registry.code_executor.execute(kw.get("code", ""))),
        BuiltinTool("terminal", "Execute shell commands", {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Shell command to execute"}},
            "required": ["command"],
        }, lambda **kw: registry.terminal.execute(kw.get("command", ""))),
        BuiltinTool("python_sandbox", "Execute Python code in restricted sandbox", {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute"}},
            "required": ["code"],
        }, lambda **kw: registry.python_sandbox.execute(kw.get("code", ""))),
        BuiltinTool("sql_executor", "Execute SQL queries", {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
            "required": ["query"],
        }, lambda **kw: registry.sql_executor.execute(kw.get("query", ""))),
        BuiltinTool("browser", "Browser automation and screenshots", {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to navigate to"}},
            "required": ["url"],
        }, lambda **kw: registry.browser.navigate(kw.get("url", ""))),
        BuiltinTool("calendar", "Manage calendar events", {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: list or create"},
                "title": {"type": "string", "description": "Event title"},
                "start_time": {"type": "string", "description": "ISO start time"},
                "end_time": {"type": "string", "description": "ISO end time"},
            },
            "required": ["action"],
        }, lambda **kw: registry.calendar.list_events(kw.get("start_time", ""), kw.get("end_time", ""))),
        BuiltinTool("email", "Send emails", {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
            },
            "required": ["to", "subject", "body"],
        }, lambda **kw: registry.email.send(kw.get("to", ""), kw.get("subject", ""), kw.get("body", ""))),
        BuiltinTool("maps", "Geocoding and directions", {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: geocode or directions"},
                "address": {"type": "string", "description": "Address to geocode"},
                "origin": {"type": "string", "description": "Origin for directions"},
                "destination": {"type": "string", "description": "Destination for directions"},
            },
            "required": ["action"],
        }, lambda **kw: registry.maps.geocode(kw.get("address", ""))),
        BuiltinTool("ocr", "Extract text from images", {
            "type": "object",
            "properties": {"image_path": {"type": "string", "description": "Path to image file"}},
            "required": ["image_path"],
        }, lambda **kw: registry.ocr.extract_text(kw.get("image_path", ""))),
        BuiltinTool("image_generator", "Generate images from text", {
            "type": "object",
            "properties": {"prompt": {"type": "string", "description": "Image description"}},
            "required": ["prompt"],
        }, lambda **kw: registry.image_generator.generate(kw.get("prompt", ""))),
        BuiltinTool("image_editor", "Edit images (resize, crop, rotate)", {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to image"},
                "action": {"type": "string", "description": "Action: resize, crop, rotate"},
                "width": {"type": "integer", "description": "Width for resize"},
                "height": {"type": "integer", "description": "Height for resize"},
            },
            "required": ["image_path", "action"],
        }, lambda **kw: registry.image_editor.resize(kw.get("image_path", ""), kw.get("width", 0), kw.get("height", 0))),
        BuiltinTool("video_generator", "Generate videos from text", {
            "type": "object",
            "properties": {"prompt": {"type": "string", "description": "Video description"}},
            "required": ["prompt"],
        }, lambda **kw: registry.video_generator.generate_from_text(kw.get("prompt", ""))),
        BuiltinTool("audio_editor", "Edit audio files (trim, convert)", {
            "type": "object",
            "properties": {
                "audio_path": {"type": "string", "description": "Path to audio file"},
                "action": {"type": "string", "description": "Action: trim or convert"},
                "start_seconds": {"type": "number", "description": "Start time for trim"},
                "end_seconds": {"type": "number", "description": "End time for trim"},
            },
            "required": ["audio_path", "action"],
        }, lambda **kw: registry.audio_editor.trim(kw.get("audio_path", ""), kw.get("start_seconds", 0.0), kw.get("end_seconds", 0.0))),
        BuiltinTool("pdf_analyzer", "Extract text and metadata from PDFs", {
            "type": "object",
            "properties": {"pdf_path": {"type": "string", "description": "Path to PDF file"}},
            "required": ["pdf_path"],
        }, lambda **kw: registry.pdf_analyzer.extract_text(kw.get("pdf_path", ""))),
        BuiltinTool("csv_analyzer", "Analyze CSV files", {
            "type": "object",
            "properties": {"csv_path": {"type": "string", "description": "Path to CSV file"}},
            "required": ["csv_path"],
        }, lambda **kw: registry.csv_analyzer.analyze(kw.get("csv_path", ""))),
        BuiltinTool("github", "GitHub integration", {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: list_repos or create_issue"},
                "username": {"type": "string", "description": "GitHub username"},
                "repo": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "Issue title"},
                "body": {"type": "string", "description": "Issue body"},
            },
            "required": ["action"],
        }, lambda **kw: registry.github.list_repos(kw.get("username", ""))),
        BuiltinTool("url_reader", "Read content from URLs", {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to read"}},
            "required": ["url"],
        }, lambda **kw: registry.url_reader.read_url(kw.get("url", ""))),
        BuiltinTool("file_reader", "Read text files", {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "Path to file"}},
            "required": ["file_path"],
        }, lambda **kw: registry.file_reader.read(kw.get("file_path", ""))),
    ]


__all__ = [
    "ToolRegistry",
    "ToolDefinition",
    "ToolCategory",
    "ToolExecutor",
    "ToolResult",
    "ToolSandbox",
    "SandboxPolicy",
    "SandboxMode",
    "ToolPermissionManager",
    "ToolAccessPolicy",
    "ToolPermission",
    "ToolSchemaValidator",
    "FunctionCallingFramework",
    "ToolCall",
    "FCToolDefinition",
    "ToolCache",
    "ToolRateLimiter",
    "ToolBuilder",
    "tool_registry",
    "CalculatorTool",
    "CodeExecutionTool",
    "WeatherTool",
    "WebSearchTool",
    "TerminalTool",
    "PythonSandboxTool",
    "SQLExecutionTool",
    "BrowserAutomationTool",
    "CalendarTool",
    "EmailTool",
    "MapsTool",
    "OCRTool",
    "ImageGenerationTool",
    "ImageEditingTool",
    "VideoGenerationTool",
    "AudioEditingTool",
    "PDFAnalysisTool",
    "CSVAnalysisTool",
    "GitHubIntegrationTool",
    "URLReaderTool",
    "FileReaderTool",
    "BuiltinTool",
    "get_builtin_tools",
]
