import json
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "registry"
DATASETS_DIR = REGISTRY_DIR / "versions"
CARDS_DIR = REGISTRY_DIR / "cards"
MANIFEST_PATH = REGISTRY_DIR / "manifest.json"


def _ensure_dirs() -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    CARDS_DIR.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"version": "1.0.0", "datasets": {}, "aliases": {}}


def _save_manifest(data: Dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(data, indent=2, default=str))


def register_dataset(
    name: str,
    version: str,
    dataset_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    aliases: Optional[List[str]] = None,
    status: str = "registered",
) -> Dict[str, Any]:
    _ensure_dirs()
    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    dataset_sha = _sha256_file(dataset_file)
    version_dir = DATASETS_DIR / name / version
    version_dir.mkdir(parents=True, exist_ok=True)
    dest = version_dir / dataset_file.name
    shutil.copy2(dataset_file, dest)

    record = {
        "name": name,
        "version": version,
        "sha256": dataset_sha,
        "file": str(dest.relative_to(REGISTRY_DIR)),
        "size_bytes": dest.stat().st_size,
        "registered_at": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "metadata": metadata or {},
        "statistics": {},
    }

    manifest = _load_manifest()
    if name not in manifest["datasets"]:
        manifest["datasets"][name] = {}
    manifest["datasets"][name][version] = record

    if aliases:
        for alias in aliases:
            manifest["aliases"][alias] = f"{name}:{version}"

    _save_manifest(manifest)
    return record


def get_dataset(name: str, version: Optional[str] = None) -> Dict[str, Any]:
    manifest = _load_manifest()
    if name not in manifest["datasets"]:
        raise KeyError(f"Dataset not found: {name}")
    versions = manifest["datasets"][name]
    if version is None:
        version = sorted(versions.keys())[-1]
    if version not in versions:
        raise KeyError(f"Dataset version not found: {name}:{version}")
    return versions[version]


def list_datasets() -> List[Dict[str, Any]]:
    manifest = _load_manifest()
    result = []
    for name, versions in manifest["datasets"].items():
        latest = sorted(versions.keys())[-1]
        result.append({
            "name": name,
            "latest_version": latest,
            "versions": list(versions.keys()),
            "latest_status": versions[latest].get("status"),
        })
    return result


def set_alias(alias: str, name: str, version: str) -> None:
    manifest = _load_manifest()
    if name not in manifest["datasets"] or version not in manifest["datasets"][name]:
        raise KeyError(f"Dataset version not found: {name}:{version}")
    manifest["aliases"][alias] = f"{name}:{version}"
    _save_manifest(manifest)


def resolve_alias(alias: str) -> str:
    manifest = _load_manifest()
    if alias not in manifest["aliases"]:
        raise KeyError(f"Alias not found: {alias}")
    return manifest["aliases"][alias]


def update_dataset_status(name: str, version: str, status: str) -> None:
    manifest = _load_manifest()
    if name not in manifest["datasets"] or version not in manifest["datasets"][name]:
        raise KeyError(f"Dataset version not found: {name}:{version}")
    manifest["datasets"][name][version]["status"] = status
    manifest["datasets"][name][version]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save_manifest(manifest)


def update_dataset_statistics(name: str, version: str, statistics: Dict[str, Any]) -> None:
    manifest = _load_manifest()
    if name not in manifest["datasets"] or version not in manifest["datasets"][name]:
        raise KeyError(f"Dataset version not found: {name}:{version}")
    manifest["datasets"][name][version]["statistics"] = statistics
    _save_manifest(manifest)
