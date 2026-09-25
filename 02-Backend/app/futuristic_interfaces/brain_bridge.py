import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BrainToComputerBridge:
    def __init__(self) -> None:
        self._command_registry: dict[str, dict[str, Any]] = {
            "open_app": {"params": ["app_name"], "confirmation": False},
            "close_app": {"params": ["app_name"], "confirmation": True},
            "scroll": {"params": ["direction", "amount"], "confirmation": False},
            "click": {"params": ["x", "y"], "confirmation": False},
            "type": {"params": ["text"], "confirmation": False},
            "volume_up": {"params": [], "confirmation": False},
            "volume_down": {"params": [], "confirmation": False},
            "home": {"params": [], "confirmation": False},
            "back": {"params": [], "confirmation": False},
            "confirm": {"params": [], "confirmation": False},
        }
        self._history: list[dict[str, Any]] = []

    def execute_command(self, command: str, parameters: dict[str, Any], confidence_threshold: float) -> dict[str, Any]:
        if command not in self._command_registry:
            return {
                "status": "error",
                "command": command,
                "error": f"Unknown command: {command}",
            }

        confidence = parameters.get("confidence", 0.9)
        if confidence < confidence_threshold:
            return {
                "status": "rejected",
                "command": command,
                "reason": "confidence_below_threshold",
                "confidence": confidence,
                "threshold": confidence_threshold,
            }

        entry = {
            "command": command,
            "parameters": parameters,
            "confidence": confidence,
            "status": "executed",
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            )),
        }
        self._history.append(entry)
        return entry

    def get_status(self) -> dict[str, Any]:
        return {
            "registered_commands": list(self._command_registry.keys()),
            "execution_count": len(self._history),
            "recent_commands": self._history[-10:],
        }
