import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactStorage:
    def __init__(self, experiment_id: str, storage_dir: Optional[Path] = None):
        self.experiment_id = experiment_id
        self._storage_dir = storage_dir or Path(__file__).resolve().parent.parent.parent / "experiments" / "artifacts"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: List[Dict[str, Any]] = []

    def store(self, name: str, source_path: str, artifact_type: str = "file") -> Dict[str, Any]:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Artifact source not found: {source_path}")

        dest_dir = self._storage_dir / self.experiment_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
        shutil.copy2(source, dest)

        artifact_hash = self._sha256_file(dest)
        record = {
            "name": name,
            "type": artifact_type,
            "path": str(dest),
            "relative_path": str(dest.relative_to(self._storage_dir)),
            "sha256": artifact_hash,
            "size_bytes": dest.stat().st_size,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self._artifacts.append(record)
        return record

    def store_string(self, name: str, content: str, artifact_type: str = "text") -> Dict[str, Any]:
        dest_dir = self._storage_dir / self.experiment_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / name
        dest.write_text(content)
        artifact_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = {
            "name": name,
            "type": artifact_type,
            "path": str(dest),
            "relative_path": str(dest.relative_to(self._storage_dir)),
            "sha256": artifact_hash,
            "size_bytes": len(content.encode("utf-8")),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self._artifacts.append(record)
        return record

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        for artifact in self._artifacts:
            if artifact["name"] == name:
                return artifact
        return None

    def list_artifacts(self) -> List[Dict[str, Any]]:
        return list(self._artifacts)

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "artifacts": self._artifacts,
            "storage_dir": str(self._storage_dir),
        }

    def save(self) -> Path:
        path = self._storage_dir / f"{self.experiment_id}_manifest.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        return path
