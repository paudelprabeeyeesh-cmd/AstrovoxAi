"""
Scripting engine for automation with sandboxed execution.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Script:
    name: str
    source: str
    environment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScriptResult:
    success: bool
    output: Any = None
    error: Optional[str] = None


class ScriptingEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._scripts: Dict[str, Script] = {}
        self._results: Dict[str, ScriptResult] = {}

    def register(self, script: Script) -> None:
        with self._lock:
            self._scripts[script.name] = script

    def run(self, name: str, context: Optional[Dict[str, Any]] = None) -> ScriptResult:
        with self._lock:
            script = self._scripts.get(name)
        if not script:
            return ScriptResult(success=False, error="script not found")
        env: Dict[str, Any] = {}
        env.update(script.environment)
        if context:
            env.update(context)
        try:
            exec(script.source, {"__builtins__": {}}, env)  # noqa: S102
            output = env.get("result")
            result = ScriptResult(success=True, output=output)
        except Exception as exc:
            result = ScriptResult(success=False, error=str(exc))
        with self._lock:
            self._results[name] = result
        return result

    def result(self, name: str) -> Optional[ScriptResult]:
        with self._lock:
            return self._results.get(name)

    def list_scripts(self) -> List[str]:
        with self._lock:
            return list(self._scripts.keys())
