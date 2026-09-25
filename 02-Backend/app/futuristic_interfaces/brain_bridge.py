import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BridgeCommand:
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    status: str = "pending"
    executed_at: float = field(default_factory=time.time)


class BrainToComputerBridge:
    COMMAND_REGISTRY = {
        "open_app": {"params": ["app_name"], "confirmation": False, "category": "navigation"},
        "close_app": {"params": ["app_name"], "confirmation": True, "category": "navigation"},
        "scroll": {"params": ["direction", "amount"], "confirmation": False, "category": "navigation"},
        "click": {"params": ["x", "y"], "confirmation": False, "category": "input"},
        "type": {"params": ["text"], "confirmation": False, "category": "input"},
        "volume_up": {"params": [], "confirmation": False, "category": "system"},
        "volume_down": {"params": [], "confirmation": False, "category": "system"},
        "home": {"params": [], "confirmation": False, "category": "navigation"},
        "back": {"params": [], "confirmation": False, "category": "navigation"},
        "confirm": {"params": [], "confirmation": False, "category": "input"},
        "copy": {"params": [], "confirmation": False, "category": "input"},
        "paste": {"params": [], "confirmation": False, "category": "input"},
        "search": {"params": ["query"], "confirmation": False, "category": "navigation"},
        "switch_window": {"params": ["direction"], "confirmation": False, "category": "navigation"},
        "screenshot": {"params": [], "confirmation": False, "category": "system"},
    }

    def __init__(self) -> None:
        self._history: list[BridgeCommand] = []
        self._registry = dict(self.COMMAND_REGISTRY)

    def execute_command(self, command: str, parameters: dict[str, Any], confidence_threshold: float) -> dict[str, Any]:
        if command not in self._registry:
            return {
                "status": "error",
                "command": command,
                "error": f"Unknown command: {command}",
                "available_commands": list(self._registry.keys()),
            }

        confidence = parameters.get("confidence", 0.9)
        if confidence < confidence_threshold:
            entry = BridgeCommand(
                command=command,
                parameters=parameters,
                confidence=confidence,
                status="rejected",
            )
            self._history.append(entry)
            return {
                "status": "rejected",
                "command_id": entry.command_id,
                "command": command,
                "reason": "confidence_below_threshold",
                "confidence": confidence,
                "threshold": confidence_threshold,
            }

        entry = BridgeCommand(
            command=command,
            parameters=parameters,
            confidence=confidence,
            status="executed",
        )
        self._history.append(entry)
        logger.info("Brain bridge executed: command=%s confidence=%.2f", command, confidence)
        return {
            "status": "executed",
            "command_id": entry.command_id,
            "command": command,
            "parameters": parameters,
            "confidence": confidence,
            "timestamp": entry.executed_at,
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "registered_commands": list(self._registry.keys()),
            "execution_count": len(self._history),
            "recent_commands": [
                {
                    "command_id": c.command_id,
                    "command": c.command,
                    "confidence": c.confidence,
                    "status": c.status,
                    "timestamp": c.executed_at,
                }
                for c in self._history[-10:]
            ],
        }

    def register_command(self, command: str, params: list[str], confirmation: bool = False, category: str = "custom") -> dict[str, Any]:
        if command in self._registry:
            return {"status": "exists", "command": command}
        self._registry[command] = {
            "params": params,
            "confirmation": confirmation,
            "category": category,
        }
        return {"status": "registered", "command": command, "params": params, "category": category}
