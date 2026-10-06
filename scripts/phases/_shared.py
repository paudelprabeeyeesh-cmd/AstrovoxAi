"""Shared utilities for phase builders."""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
MODULES_DIR = BASE / "astrovox" / "phases"
TESTS_DIR = BASE / "tests" / "phases"


def write_module(name: str, code: str) -> None:
    """Write a phase module to astrovox/phases/phase{name}.py."""
    path = MODULES_DIR / f"phase{name}.py"
    path.write_text(code)


def ensure_dirs() -> None:
    """Ensure output directories exist."""
    MODULES_DIR.mkdir(parents=True, exist_ok=True)
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
