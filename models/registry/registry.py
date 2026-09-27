import json
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "registry"
MODELS_DIR = REGISTRY_DIR / "versions"
CARDS_DIR = REGISTRY_DIR / "cards"
MANIFEST_PATH = REGISTRY_DIR / "manifest.json"


def _ensure_dirs() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
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
    return {"version": "1.0.0", "models": {}, "aliases": {}}


def _save_manifest(data: Dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(data, indent=2, default=str))


def register_model(
    name: str,
    version: str,
    model_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    aliases: Optional[List[str]] = None,
    status: str = "registered",
) -> Dict[str, Any]:
    _ensure_dirs()
    model_file = Path(model_path)
    if not model_file.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model_sha = _sha256_file(model_file)
    version_dir = MODELS_DIR / name / version
    version_dir.mkdir(parents=True, exist_ok=True)
    dest = version_dir / model_file.name
    shutil.copy2(model_file, dest)

    record = {
        "name": name,
        "version": version,
        "sha256": model_sha,
        "file": str(dest.relative_to(REGISTRY_DIR)),
        "size_bytes": dest.stat().st_size,
        "registered_at": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "metadata": metadata or {},
        "evaluation": {},
    }

    manifest = _load_manifest()
    if name not in manifest["models"]:
        manifest["models"][name] = {}
    manifest["models"][name][version] = record

    if aliases:
        for alias in aliases:
            manifest["aliases"][alias] = f"{name}:{version}"

    _save_manifest(manifest)
    return record


def get_model(name: str, version: Optional[str] = None) -> Dict[str, Any]:
    manifest = _load_manifest()
    if name not in manifest["models"]:
        raise KeyError(f"Model not found: {name}")
    versions = manifest["models"][name]
    if version is None:
        version = sorted(versions.keys())[-1]
    if version not in versions:
        raise KeyError(f"Model version not found: {name}:{version}")
    return versions[version]


def list_models() -> List[Dict[str, Any]]:
    manifest = _load_manifest()
    result = []
    for name, versions in manifest["models"].items():
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
    if name not in manifest["models"] or version not in manifest["models"][name]:
        raise KeyError(f"Model version not found: {name}:{version}")
    manifest["aliases"][alias] = f"{name}:{version}"
    _save_manifest(manifest)


def resolve_alias(alias: str) -> str:
    manifest = _load_manifest()
    if alias not in manifest["aliases"]:
        raise KeyError(f"Alias not found: {alias}")
    return manifest["aliases"][alias]


def update_model_status(name: str, version: str, status: str) -> None:
    manifest = _load_manifest()
    if name not in manifest["models"] or version not in manifest["models"][name]:
        raise KeyError(f"Model version not found: {name}:{version}")
    manifest["models"][name][version]["status"] = status
    manifest["models"][name][version]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save_manifest(manifest)


def compare_models(name: str, versions: List[str]) -> Dict[str, Any]:
    manifest = _load_manifest()
    if name not in manifest["models"]:
        raise KeyError(f"Model not found: {name}")
    results = {}
    for v in versions:
        if v not in manifest["models"][name]:
            raise KeyError(f"Version not found: {name}:{v}")
        results[v] = manifest["models"][name][v]
    return results
