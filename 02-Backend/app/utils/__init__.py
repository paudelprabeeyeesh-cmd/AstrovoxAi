"""Utility package for AstrovoxAI backend."""

import importlib.util
import os
from pathlib import Path
from typing import Any

_utils_path = Path(__file__).parent / "utils.py"
_spec = importlib.util.spec_from_file_location("app._utils_module", _utils_path)
_utils_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utils_module)

BackoffStrategy = _utils_module.BackoffStrategy
CircuitState = _utils_module.CircuitState
generate_id = _utils_module.generate_id
auto_tag = _utils_module.auto_tag
auto_summary = _utils_module.auto_summary
truncate = _utils_module.truncate
backoff_delay = _utils_module.backoff_delay
now = _utils_module.now

__all__ = [
    "BackoffStrategy",
    "CircuitState",
    "generate_id",
    "auto_tag",
    "auto_summary",
    "truncate",
    "backoff_delay",
    "now",
]
