from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib
import json
import os
import platform

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentSnapshot:
    python_version: str
    platform: str
    hardware: Dict[str, Any]
    software: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class ReproducibilityResult:
    experiment_id: str
    seed: int
    snapshot: EnvironmentSnapshot
    metrics: Dict[str, Any]
    comparable: bool
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class SeedManager:
    def __init__(self):
        self.current_seed: int = 42

    def set(self, seed: int) -> int:
        self.current_seed = seed
        self._apply(seed)
        logger.info("Seed set to %d", seed)
        return seed

    def get(self) -> int:
        return self.current_seed

    def _apply(self, seed: int) -> None:
        import random
        import numpy as np
        import torch
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if torch.mps.is_available():
            torch.mps.manual_seed(seed)

    def state(self) -> Dict:
        import random
        import numpy as np
        import torch
        return {
            "seed": self.current_seed,
            "python_state": random.getstate(),
            "numpy_state": np.random.get_state()[1].tobytes()[:16].hex(),
            "torch_state": torch.random.get_rng_state().tolist()[:8],
        }


class HardwareDetector:
    @staticmethod
    def detect() -> Dict[str, Any]:
        import torch
        cpu_info = {"device": torch.cpu.get_device_name() if hasattr(torch.cpu, "get_device_name") else "unknown"}
        cuda_info = {"available": torch.cuda.is_available(), "count": torch.cuda.device_count(), "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "n/a", "memory_mb": torch.cuda.get_device_properties(0).total_memory // (1024 ** 2) if torch.cuda.is_available() else 0}
        mps_info = {"available": torch.mps.is_available(), "device": torch.mps.current_device() if torch.mps.is_available() else "n/a"}
        return {"cpu": cpu_info, "cuda": cuda_info, "mps": mps_info}

    @staticmethod
    def summary() -> str:
        hw = HardwareDetector.detect()
        cuda = hw["cuda"]
        return f"CUDA={cuda['available']} devices={cuda['count']} memory={cuda.get('memory_mb', 0)}MB"


class EnvironmentSnapshotter:
    @staticmethod
    def capture() -> EnvironmentSnapshot:
        import sys
        import torch
        hw = HardwareDetector.detect()
        sw = {
            "python_version": sys.version,
            "torch_version": torch.__version__,
            "platform": platform.platform(),
        }
        return EnvironmentSnapshot(python_version=sw["python_version"], platform=sw["platform"], hardware=hw, software=sw)

    @staticmethod
    def to_hash(snapshot: EnvironmentSnapshot) -> str:
        raw = json.dumps(snapshot.__dict__, default=str, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def diff(a: EnvironmentSnapshot, b: EnvironmentSnapshot) -> Dict[str, Any]:
        diffs: Dict[str, Any] = {"hardware": {}, "software": {}, "changed": False}
        for section in ["hardware", "software"]:
            sa = getattr(a, section)
            sb = getattr(b, section)
            for k in set(sa) | set(sb):
                if sa.get(k) != sb.get(k):
                    diffs[section][k] = {"a": sa.get(k), "b": sb.get(k)}
                    diffs["changed"] = True
        return diffs


class ResultComparator:
    @staticmethod
    def compare(metrics_a: Dict[str, Any], metrics_b: Dict[str, Any], tolerance: float = 1e-5) -> Dict[str, Any]:
        differences = {}
        for key in set(metrics_a) | set(metrics_b):
            val_a = metrics_a.get(key)
            val_b = metrics_b.get(key)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diff = abs(val_a - val_b)
                if diff > tolerance:
                    differences[key] = {"a": val_a, "b": val_b, "diff": diff}
        return {"similar": len(differences) == 0, "differences": differences, "tolerance": tolerance}

    @staticmethod
    def compare_metric_history(history_a: List[Dict], history_b: List[Dict], tolerance: float = 1e-5) -> Dict[str, Any]:
        if len(history_a) != len(history_b):
            return {"similar": False, "reason": f"history length mismatch: {len(history_a)} vs {len(history_b)}"}
        all_diffs = []
        for step_a, step_b in zip(history_a, history_b, strict=False):
            for k in set(step_a) | set(step_b):
                va = step_a.get(k)
                vb = step_b.get(k)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    diff = abs(va - vb)
                    if diff > tolerance:
                        all_diffs.append({"step": step_a.get("step"), "key": k, "diff": diff, "a": va, "b": vb})
        return {"similar": len(all_diffs) == 0, "differences": all_diffs, "tolerance": tolerance}


class ReproducibilityFramework:
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.seed_manager = SeedManager()
        self.snapshotter = EnvironmentSnapshotter()
        self.comparator = ResultComparator()

    def record(self, metrics: Dict[str, Any]) -> ReproducibilityResult:
        snapshot = self.snapshotter.capture()
        return ReproducibilityResult(experiment_id=self.experiment_id, seed=self.seed_manager.get(), snapshot=snapshot, metrics=metrics, comparable=True)

    def compare(self, result_a: ReproducibilityResult, result_b: ReproducibilityResult) -> Dict[str, Any]:
        env_diff = EnvironmentSnapshotter.diff(result_a.snapshot, result_b.snapshot)
        metric_diff = self.comparator.compare(result_a.metrics, result_b.metrics)
        return {"environments_similar": not env_diff["changed"], "metrics_similar": metric_diff["similar"], "environment_diff": env_diff, "metric_diff": metric_diff}
