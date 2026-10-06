"""Debugging agent: analyzes errors and proposes fixes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Diagnosis:
    """Diagnosis of an error."""
    error_type: str = ""
    root_cause: str = ""
    suggested_fix: str = ""
    confidence: float = 0.0
    files_affected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"error_type": self.error_type, "root_cause": self.root_cause,
                "suggested_fix": self.suggested_fix, "confidence": self.confidence,
                "files_affected": self.files_affected}


class DebuggingAgent:
    """Agent that diagnoses errors and proposes fixes."""

    def __init__(self, name: str = "debugger"):
        self.name = name
        self.role = "debugger"
        self.history: list[Diagnosis] = []

    def plan(self, error: str) -> dict:
        return {"action": "diagnose", "error": error}

    def act(self, action: dict) -> Diagnosis:
        error = action.get("error", action.get("description", ""))
        exc_type = type(error).__name__
        diagnosis = Diagnosis(
            error_type=exc_type,
            root_cause=f"root cause of: {error[:100]}",
            suggested_fix=f"fix: resolve {error[:60]} at the indicated location",
            confidence=0.7,
            files_affected=[]
        )
        self.history.append({"error": error, "diagnosis": diagnosis.to_dict()})
        return diagnosis

    def diagnose(self, error: str) -> Diagnosis:
        return self.act({"action": "diagnose", "error": error})

    def fix(self, error: str, file_path: str) -> str:
        """Return a suggested code fix for the error."""
        diag = self.diagnose(error)
        return f"--- fix for {file_path}\n" f"# {diag.suggested_fix}\n"
