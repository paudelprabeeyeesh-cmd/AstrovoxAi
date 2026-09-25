import logging
import ast
import hashlib
import json
import os
import re
import tempfile
import textwrap
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class SafetyConstraintViolation(Exception):
    pass


class LoopStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ImprovementIteration:
    iteration_id: str
    loop_id: str
    metric: str
    baseline: float
    current: float
    delta: float
    strategy: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SelfImprovementLoop:
    loop_id: str
    target_module: str
    metric: str
    safety_constraints: list[str] = field(default_factory=list)
    max_iterations: int = 10
    improvement_threshold: float = 0.05
    status: LoopStatus = LoopStatus.RUNNING
    iterations: list[ImprovementIteration] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class RecursiveSelfImprovementService:
    def __init__(self) -> None:
        self._loops: dict[str, SelfImprovementLoop] = {}
        self._lock = threading.Lock()
        self._max_patch_bytes = 4096
        self._allowed_modules: set[str] = set()
        self._forbidden_imports: set[str] = {"os", "subprocess", "sys", "shutil", "socket"}
        self._history: list[ImprovementIteration] = []
        self._load_safety_config()

    def _load_safety_config(self) -> None:
        try:
            raw = os.getenv("ASTROVOX_SELF_IMPROVE_ALLOWED_MODULES", "")
            self._allowed_modules = {m.strip() for m in raw.split(",") if m.strip()}
        except Exception:
            self._allowed_modules = set()

    def register_module(self, module_name: str) -> None:
        self._allowed_modules.add(module_name)

    def is_module_allowed(self, module_name: str) -> bool:
        if not self._allowed_modules:
            return True
        return module_name in self._allowed_modules

    def start_loop(self, loop_id: str, target_module: str, params: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if loop_id in self._loops:
                return {"loop_id": loop_id, "status": "already_running"}

            constraints = list(params.get("safety_constraints", []))
            loop = SelfImprovementLoop(
                loop_id=loop_id,
                target_module=target_module,
                metric=params.get("metric", "response_quality"),
                safety_constraints=constraints,
                max_iterations=int(params.get("max_iterations", 10)),
                improvement_threshold=float(params.get("improvement_threshold", 0.05)),
            )
            self._loops[loop_id] = loop
            logger.info("Started self-improvement loop %s for module %s", loop_id, target_module)
            return {"loop_id": loop_id, "status": "started", "target_module": target_module}

    def iterate(self, loop_id: str, candidate_patch: str | None = None) -> dict[str, Any]:
        with self._lock:
            loop = self._loops.get(loop_id)
            if not loop:
                return {"loop_id": loop_id, "status": "not_found"}
            if loop.status != LoopStatus.RUNNING:
                return {"loop_id": loop_id, "status": loop.status}

            iteration_num = len(loop.iterations) + 1
            if iteration_num > loop.max_iterations:
                loop.status = LoopStatus.STOPPED
                return {"loop_id": loop_id, "status": "max_iterations_reached"}

            baseline = self._measure_metric(loop.target_module, loop.metric, loop.iterations)
            current = baseline
            delta = 0.0
            strategy = "noop"

            if candidate_patch:
                strategy = "llm_patch"
                try:
                    self._apply_safe_patch(loop.target_module, candidate_patch)
                    current = self._measure_metric(loop.target_module, loop.metric, loop.iterations)
                    delta = current - baseline
                except SafetyConstraintViolation as exc:
                    logger.error("Patch rejected for loop %s: %s", loop_id, exc)
                    return {"loop_id": loop_id, "status": "patch_rejected", "reason": str(exc)}
                except Exception as exc:
                    logger.error("Patch application failed for loop %s: %s", loop_id, exc)
                    return {"loop_id": loop_id, "status": "error", "error": str(exc)}

            iteration = ImprovementIteration(
                iteration_id=str(uuid.uuid4()),
                loop_id=loop_id,
                metric=loop.metric,
                baseline=baseline,
                current=current,
                delta=delta,
                strategy=strategy,
            )
            loop.iterations.append(iteration)
            self._history.append(iteration)

            if abs(delta) >= loop.improvement_threshold and delta > 0:
                logger.info(
                    "Loop %s improved %s by %.4f in iteration %d", loop_id, loop.metric, delta, iteration_num
                )
            elif delta < -loop.improvement_threshold:
                logger.warning("Loop %s regression detected in iteration %d", loop_id, iteration_num)

            return {
                "loop_id": loop_id,
                "iteration": iteration_num,
                "status": loop.status,
                "metric": loop.metric,
                "baseline": round(baseline, 4),
                "current": round(current, 4),
                "delta": round(delta, 4),
                "strategy": strategy,
            }

    def stop_loop(self, loop_id: str) -> dict[str, Any]:
        with self._lock:
            loop = self._loops.get(loop_id)
            if not loop:
                return {"loop_id": loop_id, "status": "not_found"}
            loop.status = LoopStatus.STOPPED
            return {"loop_id": loop_id, "status": "stopped"}

    def pause_loop(self, loop_id: str) -> dict[str, Any]:
        with self._lock:
            loop = self._loops.get(loop_id)
            if not loop:
                return {"loop_id": loop_id, "status": "not_found"}
            loop.status = LoopStatus.PAUSED
            return {"loop_id": loop_id, "status": "paused"}

    def resume_loop(self, loop_id: str) -> dict[str, Any]:
        with self._lock:
            loop = self._loops.get(loop_id)
            if not loop:
                return {"loop_id": loop_id, "status": "not_found"}
            loop.status = LoopStatus.RUNNING
            return {"loop_id": loop_id, "status": "running"}

    def get_status(self, loop_id: str) -> dict[str, Any]:
        loop = self._loops.get(loop_id)
        if not loop:
            return {"loop_id": loop_id, "status": "not_found"}
        return {
            "loop_id": loop.loop_id,
            "status": loop.status,
            "target_module": loop.target_module,
            "metric": loop.metric,
            "iterations": len(loop.iterations),
            "max_iterations": loop.max_iterations,
            "improvement_threshold": loop.improvement_threshold,
        }

    def _measure_metric(self, module_name: str, metric: str, history: list[ImprovementIteration]) -> float:
        if history:
            return history[-1].current + (hash(module_name + metric) % 100) / 10000.0
        return 0.5

    def _validate_patch(self, module_name: str, patch: str) -> None:
        if len(patch.encode("utf-8")) > self._max_patch_bytes:
            raise SafetyConstraintViolation("patch_too_large")

        if not self.is_module_allowed(module_name):
            raise SafetyConstraintViolation(f"module_not_allowed: {module_name}")

        forbidden = [f"import {name}" for name in self._forbidden_imports]
        for token in forbidden:
            if token in patch:
                raise SafetyConstraintViolation(f"forbidden_import: {token}")

        try:
            ast.parse(patch)
        except SyntaxError as exc:
            raise SafetyConstraintViolation(f"invalid_syntax: {exc}")

    def _apply_safe_patch(self, module_name: str, patch: str) -> None:
        self._validate_patch(module_name, patch)
        target_hash = hashlib.sha256(module_name.encode()).hexdigest()[:8]
        patch_dir = os.path.join(tempfile.gettempdir(), "astrovox_self_improve")
        os.makedirs(patch_dir, exist_ok=True)
        patch_path = os.path.join(patch_dir, f"{target_hash}_{int(time.time())}.py")
        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(patch)
        logger.debug("Patch staged at %s for module %s", patch_path, module_name)

    def get_history(self, loop_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        items = self._history
        if loop_id:
            items = [i for i in items if i.loop_id == loop_id]
        items = sorted(items, key=lambda i: i.timestamp, reverse=True)[:limit]
        return [
            {
                "iteration_id": i.iteration_id,
                "loop_id": i.loop_id,
                "metric": i.metric,
                "baseline": round(i.baseline, 4),
                "current": round(i.current, 4),
                "delta": round(i.delta, 4),
                "strategy": i.strategy,
                "timestamp": i.timestamp,
            }
            for i in items
        ]
