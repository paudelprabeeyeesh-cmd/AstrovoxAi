"""Robotics integration hooks and adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RobotTelemetry:
    robot_id: str
    joint_positions: list[float] = field(default_factory=list)
    velocities: list[float] = field(default_factory=list)
    force_torque: list[float] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class ControlCommand:
    robot_id: str
    joint_targets: list[float]
    gripper: float | None = None
    duration_s: float = 0.0


class RoboticsAdapter:
    def __init__(self, backend: str = "mock"):
        self.backend = backend
        self._client = None

    def connect(self, endpoint: str) -> None:
        logger.info("Connecting to robotics backend %s at %s", self.backend, endpoint)
        self._client = endpoint

    def send_command(self, command: ControlCommand) -> bool:
        logger.debug("Sending command to %s: %s", command.robot_id, command.joint_targets)
        return True

    def read_telemetry(self, robot_id: str) -> RobotTelemetry:
        return RobotTelemetry(robot_id=robot_id, timestamp=0.0)

    def shutdown(self) -> None:
        self._client = None


class VLAHook:
    def __init__(self, model: Any | None = None):
        self.model = model

    def plan(self, instruction: str, observation: dict[str, Any]) -> list[float]:
        return []

    def execute(self, plan: list[float]) -> bool:
        return True
