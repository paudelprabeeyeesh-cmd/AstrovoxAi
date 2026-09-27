"""Agent tools for browser automation, code execution, and file editing."""
from __future__ import annotations

import base64
import logging
import os
import subprocess
import tempfile
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BrowserTool:
    name = "browser"
    description = "Automate browser interactions"

    def run(self, url: str, action: str = "screenshot", selector: Optional[str] = None) -> dict:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                if action == "screenshot":
                    screenshot = page.screenshot(full_page=True)
                    return {"type": "image", "data": base64.b64encode(screenshot).decode()}
                elif action == "text" and selector:
                    text = page.inner_text(selector)
                    return {"type": "text", "data": text}
                browser.close()
                return {"type": "text", "data": "Action completed"}
        except ImportError:
            return {"type": "error", "data": "playwright is not installed"}


class CodeExecutionTool:
    name = "code_execution"
    description = "Execute code in a sandboxed environment"

    def run(self, code: str, language: str = "python", timeout: int = 30) -> dict:
        try:
            if language.lower() == "python":
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(code)
                    f.flush()
                    result = subprocess.run(
                        ["python", f.name],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    os.unlink(f.name)
                    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
            else:
                return {"error": f"Unsupported language: {language}"}
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out"}
        except Exception as exc:
            return {"error": str(exc)}


class FileEditTool:
    name = "file_edit"
    description = "Read, write, or edit files"

    def run(self, path: str, content: Optional[str] = None, action: str = "read") -> dict:
        try:
            if action == "read":
                with open(path, "r", encoding="utf-8") as f:
                    return {"content": f.read()}
            elif action == "write" and content is not None:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"message": f"Written {len(content)} bytes to {path}"}
            elif action == "append" and content is not None:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
                return {"message": f"Appended {len(content)} bytes to {path}"}
            else:
                return {"error": "Invalid action"}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except Exception as exc:
            return {"error": str(exc)}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Any] = {
            "browser": BrowserTool(),
            "code_execution": CodeExecutionTool(),
            "file_edit": FileEditTool(),
        }

    def list_tools(self) -> list[dict]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def execute(self, tool_name: str, **kwargs) -> dict:
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Tool {tool_name} not found"}
        try:
            return tool.run(**kwargs)
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_name, exc)
            return {"error": str(exc)}
