"""Shared exception hierarchy for AstrovoxAI.

All public modules should import exceptions from here instead of defining
their own base error classes.
"""

from __future__ import annotations

import time


class AstrovoxError(Exception):
    """Base exception for all AstrovoxAI errors."""

    def __init__(self, message: str = "", code: str = "UNKNOWN", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = time.time()

    def __str__(self) -> str:
        if self.code and self.code != "UNKNOWN":
            return f"[{self.code}] {super().__str__()}"
        return super().__str__()


class CompilerError(AstrovoxError):
    """Raised when the DSL compiler encounters an unrecoverable error."""


class RuntimeError(AstrovoxError):
    """Raised when the executor runtime fails."""


class WorkflowError(AstrovoxError):
    """Raised for workflow engine failures."""


class PluginError(AstrovoxError):
    """Raised for plugin lifecycle or permission failures."""


class SecurityError(AstrovoxError):
    """Raised for security policy violations."""


class ConfigurationError(AstrovoxError):
    """Raised for invalid configuration."""


class DependencyError(AstrovoxError):
    """Raised when a required dependency is missing or invalid."""
