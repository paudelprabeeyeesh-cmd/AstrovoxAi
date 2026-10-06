"""Coding agent: generates, edits, and reviews code."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astrovox.phases._shared.base import BaseAgent


@dataclass
class CodeEdit:
    """A single code edit (diff-like)."""
    path: str
    start: int
    end: int
    replacement: str
    description: str = ""

    def to_dict(self) -> dict:
        return {"path": self.path, "start": self.start, "end": self.end,
                "replacement": self.replacement, "description": self.description}


@dataclass
class CodeResult:
    """Result of a code-generation or edit operation."""
    success: bool
    messages: list[str] = field(default_factory=list)
    edits: list[CodeEdit] = field(default_factory=list)
    output: str = ""

    def to_dict(self) -> dict:
        return {"success": self.success, "messages": self.messages,
                "edits": [e.to_dict() for e in self.edits], "output": self.output}


class CodeAgent(BaseAgent):
    """Agent that generates and edits code."""

    def __init__(self, name: str = "coder", sandbox: str = ""):
        super().__init__(name, role="coder")
        self.sandbox = sandbox
        self.history: list[dict] = []

    def plan(self, task: str) -> dict:
        return {"action": "edit", "description": task}

    def act(self, action: dict) -> CodeResult:
        desc = action.get("description", action.get("code", ""))
        if "edit" in action.get("action", ""):
            return self._edit(desc)
        return self._generate(desc)

    def _generate(self, spec: str) -> CodeResult:
        out = f"generated code for: {spec}\n"
        out += "```python\n"
        out += f"# placeholder for {spec}\ndef solution():\n    pass\n"
        out += "```\n"
        return CodeResult(success=True, output=out)

    def _edit(self, spec: str) -> CodeResult:
        edit = CodeEdit(path="app.py", start=1, end=1,
                        replacement=f"# edited for: {spec}", description=spec)
        return CodeResult(success=True, edits=[edit], output=edit.replacement)

    def review(self, code: str) -> list[str]:
        """Return a list of review comments for the given code."""
        comments = []
        if "pass" in code:
            comments.append("avoid bare `pass` statements")
        if "TODO" in code:
            comments.append("consider replacing TODO with implementation")
        return comments

    def run(self, spec: str, max_iterations: int = 3) -> CodeResult:
        """Generate, edit, and review code."""
        result = self.act({"action": "edit", "description": spec})
        for i in range(max_iterations):
            comments = self.review(result.output)
            if comments:
                result.messages.extend(comments)
                result.output += "\n# comments:\n" + "\n".join(comments)
        return result
