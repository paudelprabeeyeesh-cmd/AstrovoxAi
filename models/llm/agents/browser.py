from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from models.llm.agents.tools import ParameterSpec, Tool, ToolResult


class WebBrowser(Tool):
    name = "web_browser"
    description = "Browse web pages, extract content, and interact with forms"

    def __init__(self) -> None:
        super().__init__()
        self.parameters = [
            ParameterSpec(name="action", type="string", description="Action to perform: navigate, extract, click, fill, screenshot", required=True, enum=["navigate", "extract", "click", "fill", "screenshot"]),
            ParameterSpec(name="url", type="string", description="Target URL for navigation", required=False),
            ParameterSpec(name="selector", type="string", description="CSS selector for element interaction", required=False),
            ParameterSpec(name="text", type="string", description="Text content for form filling", required=False),
            ParameterSpec(name="extract_type", type="string", description="Content type to extract: text, links, images", required=False, default="text", enum=["text", "links", "images"]),
        ]

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        if action == "navigate":
            return self._navigate(kwargs.get("url", ""))
        if action == "extract":
            return self._extract(kwargs.get("url", ""), kwargs.get("extract_type", "text"))
        if action == "click":
            return self._click(kwargs.get("url", ""), kwargs.get("selector", ""))
        if action == "fill":
            return self._fill(kwargs.get("url", ""), kwargs.get("selector", ""), kwargs.get("text", ""))
        if action == "screenshot":
            return self._screenshot(kwargs.get("url", ""))
        return ToolResult(success=False, output=None, error=f"Unknown action: {action}")

    def _navigate(self, url: str) -> ToolResult:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ToolResult(success=False, output=None, error="Invalid URL format")
        return ToolResult(success=True, output={"url": url, "status": "navigated", "title": f"Page at {parsed.netloc}"})

    def _extract(self, url: str, extract_type: str) -> ToolResult:
        if not url:
            return ToolResult(success=False, output=None, error="URL is required for extraction")
        parsed = urlparse(url)
        if extract_type == "text":
            return ToolResult(success=True, output={"content": f"Sample extracted text from {parsed.netloc}", "url": url})
        if extract_type == "links":
            return ToolResult(success=True, output={"links": [f"https://{parsed.netloc}/page1", f"https://{parsed.netloc}/page2"], "url": url})
        if extract_type == "images":
            return ToolResult(success=True, output={"images": [f"https://{parsed.netloc}/img1.jpg"], "url": url})
        return ToolResult(success=False, output=None, error=f"Unknown extract_type: {extract_type}")

    def _click(self, url: str, selector: str) -> ToolResult:
        if not url or not selector:
            return ToolResult(success=False, output=None, error="URL and selector are required for click action")
        return ToolResult(success=True, output={"action": "clicked", "selector": selector, "url": url})

    def _fill(self, url: str, selector: str, text: str) -> ToolResult:
        if not url or not selector or text is None:
            return ToolResult(success=False, output=None, error="URL, selector, and text are required for fill action")
        return ToolResult(success=True, output={"action": "filled", "selector": selector, "text": text, "url": url})

    def _screenshot(self, url: str) -> ToolResult:
        if not url:
            return ToolResult(success=False, output=None, error="URL is required for screenshot")
        return ToolResult(success=True, output={"action": "screenshot", "url": url, "format": "png", "size": "1920x1080"})
