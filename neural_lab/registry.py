"""Local registry for explicitly registered experimental checkpoints."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import torch

from .training import _atomic_json


class ModelRegistry:
    """Registry scoped to a local experiment directory; never changes chat defaults."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.root / "model_registry.json"
        self._state = {"schema_version": 1, "models": [], "active_experimental_model": None,
                       "previous_experimental_model": None}
        if self.registry_file.exists():
            self._state = json.loads(self.registry_file.read_text(encoding="utf-8"))

    def register_completed_run(self, run_dir: str | Path, *, name: str, dataset_provenance: str) -> dict:
        run_path = Path(run_dir).resolve(strict=True)
        if not run_path.is_relative_to(self.root) or not run_path.is_dir():
            raise ValueError("run directory must be inside the registry root")
        if not name.strip() or len(name) > 80 or not dataset_provenance.strip():
            raise ValueError("name (1–80 chars) and dataset_provenance are required")
        job = json.loads((run_path / "job.json").read_text(encoding="utf-8"))
        if job.get("state") != "COMPLETED":
            raise ValueError("only completed training runs can be registered")
        checkpoints = [Path(value).resolve(strict=True) for value in job.get("checkpoints", [])]
        if not checkpoints:
            raise ValueError("completed run has no checkpoint")
        for checkpoint in checkpoints:
            if not checkpoint.is_relative_to(run_path) or checkpoint.stat().st_size > 128 * 1024 * 1024:
                raise ValueError("checkpoint is outside the run directory or exceeds the 128 MiB inspection limit")
        # Validate the latest checkpoint with restricted PyTorch deserialization.
        checkpoint_data = torch.load(checkpoints[-1], map_location="cpu", weights_only=True)
        if checkpoint_data.get("schema_version") != 1:
            raise ValueError("checkpoint schema version is unsupported")
        if checkpoint_data.get("config") != job.get("config"):
            raise ValueError("checkpoint configuration does not match the completed job")
        model = {
            "model_id": uuid.uuid4().hex,
            "name": name.strip(),
            "architecture": "tiny-transformer-character",
            "origin": "random_initialization",
            "configuration": {
                "model": job["config"],
                "training": job.get("training_config", {}),
            },
            "training_status": job["state"],
            "checkpoint_paths": [str(path.relative_to(self.root)) for path in checkpoints],
            "dataset_id": job.get("dataset_id"),
            "dataset_provenance": dataset_provenance.strip(),
            "evaluation_results": {},
            "compatibility_status": "experimental-only; not connected to Astrovox chat",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._state["models"].append(model)
        _atomic_json(self.registry_file, self._state)
        return model

    def list_models(self) -> list[dict]:
        return list(self._state["models"])

    def select_experimental(self, model_id: str) -> dict:
        if not any(model["model_id"] == model_id for model in self._state["models"]):
            raise KeyError("model_id is not registered")
        self._state["previous_experimental_model"] = self._state["active_experimental_model"]
        self._state["active_experimental_model"] = model_id
        _atomic_json(self.registry_file, self._state)
        return self.active_experimental()

    def rollback_experimental_selection(self) -> dict | None:
        previous = self._state["previous_experimental_model"]
        self._state["active_experimental_model"] = previous
        self._state["previous_experimental_model"] = None
        _atomic_json(self.registry_file, self._state)
        return self.active_experimental()

    def active_experimental(self) -> dict | None:
        selected = self._state["active_experimental_model"]
        return next((model for model in self._state["models"] if model["model_id"] == selected), None)
