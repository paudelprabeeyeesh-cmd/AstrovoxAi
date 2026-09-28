from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from models.llm.dataset_engineering_v2 import ProcessedDocument

logger = logging.getLogger(__name__)


@dataclass
class VersionConfig:
    versions_file: str = "data/dataset_versions.json"
    manifest_file: str = "data/manifest.json"
    incremental: bool = True


class DatasetVersionManager:
    def __init__(self, config: VersionConfig | None = None) -> None:
        self.config = config or VersionConfig()
        self.versions_file = Path(self.config.versions_file)
        self.manifest_file = Path(self.config.manifest_file)
        self.versions_file.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        self._versions: list[dict[str, Any]] = self._load_versions()

    def _load_versions(self) -> list[dict[str, Any]]:
        if self.versions_file.exists():
            try:
                with self.versions_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("Failed to load versions: %s", exc)
        return []

    def _save_versions(self) -> None:
        try:
            with self.versions_file.open("w", encoding="utf-8") as f:
                json.dump(self._versions, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save versions: %s", exc)

    def _compute_checksum(self, config: dict[str, Any]) -> str:
        payload = json.dumps(config, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def create_version(
        self,
        source: str,
        documents_count: int,
        tokens_count: int,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        version_id = datetime.now().strftime("v%Y%m%d%H%M%S")
        checksum = self._compute_checksum(config or {})
        entry = {
            "version": version_id,
            "created_at": datetime.now().isoformat(),
            "source": source,
            "documents_count": documents_count,
            "tokens_count": tokens_count,
            "config_snapshot": config or {},
            "checksum": checksum,
        }
        self._versions.append(entry)
        self._save_versions()
        self._update_manifest(entry)
        logger.info("Created version %s for %s", version_id, source)
        return entry

    def _update_manifest(self, entry: dict[str, Any]) -> None:
        manifest: dict[str, Any] = {}
        if self.manifest_file.exists():
            try:
                with self.manifest_file.open("r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}
        manifest["latest"] = entry["version"]
        manifest["versions"] = [v["version"] for v in self._versions]
        manifest["total_documents"] = sum(v["documents_count"] for v in self._versions)
        manifest["total_tokens"] = sum(v["tokens_count"] for v in self._versions)
        try:
            with self.manifest_file.open("w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save manifest: %s", exc)

    def get_versions(self) -> list[dict[str, Any]]:
        return list(self._versions)

    def get_latest(self) -> dict[str, Any] | None:
        return self._versions[-1] if self._versions else None

    def get_version(self, version_id: str) -> dict[str, Any] | None:
        for v in self._versions:
            if v["version"] == version_id:
                return v
        return None


class DataLineageTracker:
    def __init__(self, output_dir: str = "data/lineage") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lineage: list[dict[str, Any]] = []

    def record(
        self,
        stage: str,
        input_count: int,
        output_count: int,
        duration_seconds: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "stage": stage,
            "input_count": input_count,
            "output_count": output_count,
            "removed_count": input_count - output_count,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._lineage.append(entry)

    def save(self, filename: str = "lineage.json") -> Path:
        path = self.output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(self._lineage, f, indent=2, ensure_ascii=False)
        return path

    def summary(self) -> dict[str, Any]:
        if not self._lineage:
            return {}
        total_input = sum(e["input_count"] for e in self._lineage)
        total_output = sum(e["output_count"] for e in self._lineage)
        total_duration = sum(e["duration_seconds"] for e in self._lineage)
        return {
            "stages": len(self._lineage),
            "total_input": total_input,
            "total_output": total_output,
            "total_removed": total_input - total_output,
            "total_duration_seconds": total_duration,
            "throughput_docs_per_sec": total_output / total_duration if total_duration > 0 else 0.0,
        }
