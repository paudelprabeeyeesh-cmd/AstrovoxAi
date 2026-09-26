"""Task planner for coding agent workflows."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_TASK_PATTERNS = [
    (re.compile(r"refactor|rename|extract|inline|clean", re.I), "refactor"),
    (re.compile(r"test|spec|pytest|jest", re.I), "test"),
    (re.compile(r"bug|fix|issue|error|traceback", re.I), "bugfix"),
    (re.compile(r"review|audit|lint|security", re.I), "review"),
    (re.compile(r"doc|readme|comment|docstring", re.I), "docs"),
    (re.compile(r"api|openapi|swagger|route|endpoint", re.I), "api"),
    (re.compile(r"arch|layer|module|structure|design", re.I), "architecture"),
    (re.compile(r"index|graph|depend|understand", re.I), "index"),
]


class TaskPlanner:
    def plan(self, user_request: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []
        task_type = self._classify(user_request)
        if task_type == "index":
            steps.append({"action": "index", "description": "Build repository index and project graph"})
        elif task_type == "refactor":
            steps.append({"action": "analyze", "description": "Scan for code smells and refactor opportunities"})
            steps.append({"action": "refactor", "description": "Apply safe refactoring transformations"})
            steps.append({"action": "verify", "description": "Run tests and syntax checks"})
        elif task_type == "test":
            steps.append({"action": "index", "description": "Discover target symbols"})
            steps.append({"action": "generate_tests", "description": "Generate unit tests"})
            steps.append({"action": "run_tests", "description": "Execute generated tests"})
        elif task_type == "bugfix":
            steps.append({"action": "scan_bugs", "description": "Scan for bug patterns"})
            steps.append({"action": "suggest_fix", "description": "Suggest fixes for detected bugs"})
            steps.append({"action": "apply_fix", "description": "Apply patches"})
        elif task_type == "review":
            steps.append({"action": "review", "description": "Run static and style analysis"})
            steps.append({"action": "summarize", "description": "Summarize findings"})
        elif task_type == "docs":
            steps.append({"action": "index", "description": "Parse symbols and docstrings"})
            steps.append({"action": "generate_docs", "description": "Generate documentation"})
        elif task_type == "api":
            steps.append({"action": "extract_routes", "description": "Extract API routes"})
            steps.append({"action": "infer_openapi", "description": "Generate OpenAPI spec"})
            steps.append({"action": "generate_client", "description": "Generate API client"})
        elif task_type == "architecture":
            steps.append({"action": "build_graph", "description": "Build project graph"})
            steps.append({"action": "analyze_arch", "description": "Analyze architecture and anti-patterns"})
        else:
            steps.append({"action": "general", "description": "Handle as general coding task"})
        return {"task_type": task_type, "steps": steps, "context": context or {}}

    def _classify(self, request: str) -> str:
        for pattern, task_type in _TASK_PATTERNS:
            if pattern.search(request):
                return task_type
        return "general"
