#!/usr/bin/env python3
"""
Phase 15 Production Backup Script
Comprehensive backup of models, datasets, configs, experiments, and database.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO_ROOT / "backups"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_cmd(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)


def backup_file(src: Path, dest: Path) -> None:
    if src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)


def backup_models(backup_path: Path) -> List[str]:
    files = []
    models_dir = REPO_ROOT / "models" / "registry"
    if models_dir.exists():
        dest = backup_path / "models"
        shutil.copytree(models_dir, dest, dirs_exist_ok=True)
        files.append("models/")
    return files


def backup_datasets(backup_path: Path) -> List[str]:
    files = []
    datasets_dir = REPO_ROOT / "datasets" / "registry"
    if datasets_dir.exists():
        dest = backup_path / "datasets"
        shutil.copytree(datasets_dir, dest, dirs_exist_ok=True)
        files.append("datasets/")
    return files


def backup_experiments(backup_path: Path) -> List[str]:
    files = []
    exp_dir = REPO_ROOT / "experiments"
    if exp_dir.exists():
        dest = backup_path / "experiments"
        shutil.copytree(exp_dir, dest, dirs_exist_ok=True)
        files.append("experiments/")
    return files


def backup_configs(backup_path: Path) -> List[str]:
    files = []
    config_dir = REPO_ROOT / "configs"
    if config_dir.exists():
        dest = backup_path / "configs"
        shutil.copytree(config_dir, dest, dirs_exist_ok=True)
        files.append("configs/")
    return files


def backup_database(backup_path: Path) -> List[str]:
    files = []
    try:
        pg_dump = shutil.which("pg_dump")
        if pg_dump:
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url:
                dump_file = backup_path / "database.sql"
                _run_cmd(f"{pg_dump} {db_url} -f {dump_file}")
                files.append("database.sql")
    except Exception as e:
        print(f"[backup] Database backup skipped: {e}")
    return files


def backup_docker_volumes(backup_path: Path) -> List[str]:
    files = []
    try:
        volumes = ["postgres_data", "redis_data", "storage"]
        for volume in volumes:
            tar_file = backup_path / f"{volume}.tar.gz"
            _run_cmd(f"docker run --rm -v astrovox-ai_{volume}:/data -v {backup_path}:/backup alpine tar czf /backup/{volume}.tar.gz -C /data .", check=False)
            if tar_file.exists():
                files.append(f"{volume}.tar.gz")
    except Exception as e:
        print(f"[backup] Docker volumes backup skipped: {e}")
    return files


def create_backup(name: str = None, include_database: bool = False, include_docker: bool = False) -> Dict[str, Any]:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = name or f"backup_{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    backup_path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "backup_id": backup_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "files": [],
        "hashes": {},
    }

    print(f"[backup] Creating backup: {backup_name}")

    for category, func in [
        ("models", backup_models),
        ("datasets", backup_datasets),
        ("experiments", backup_experiments),
        ("configs", backup_configs),
    ]:
        category_files = func(backup_path)
        manifest["files"].extend(category_files)

    if include_database:
        db_files = backup_database(backup_path)
        manifest["files"].extend(db_files)

    if include_docker:
        docker_files = backup_docker_volumes(backup_path)
        manifest["files"].extend(docker_files)

    for root, dirs, files in os.walk(backup_path):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            file_path = Path(root) / file
            rel = file_path.relative_to(backup_path)
            try:
                manifest["hashes"][str(rel)] = _sha256_file(file_path)
            except Exception:
                pass

    manifest_path = backup_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
    print(f"[backup] Backup complete: {backup_path}")
    print(f"[backup] Files: {manifest['files']}")
    return manifest


def list_backups() -> List[Dict[str, Any]]:
    if not BACKUP_DIR.exists():
        return []
    results = []
    for path in sorted(BACKUP_DIR.iterdir()):
        if path.is_dir():
            manifest_path = path / "manifest.json"
            if manifest_path.exists():
                try:
                    data = json.loads(manifest_path.read_text())
                    data["path"] = str(path)
                    results.append(data)
                except Exception:
                    pass
    return results


def main():
    parser = argparse.ArgumentParser(description="Phase 15 Backup Script")
    parser.add_argument("--name", help="Backup name")
    parser.add_argument("--database", action="store_true", help="Include database backup")
    parser.add_argument("--docker", action="store_true", help="Include Docker volumes")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    args = parser.parse_args()

    if args.list:
        backups = list_backups()
        for b in backups:
            print(f"{b['backup_id']}: {len(b['files'])} files at {b.get('path', 'N/A')}")
        return

    manifest = create_backup(args.name, args.database, args.docker)
    size = sum(
        (BACKUP_DIR / manifest["backup_id"] / f).stat().st_size
        for f in manifest["files"]
        if (BACKUP_DIR / manifest["backup_id"] / f).exists()
    )
    print(f"Backup size: {size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
