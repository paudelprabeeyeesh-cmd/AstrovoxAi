#!/usr/bin/env python3
"""
Phase 15 Production Restore Script
Restore from backups with integrity verification.
"""

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO_ROOT / "backups"


def _run_cmd(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)


def verify_backup(backup_path: Path) -> dict[str, Any]:
    manifest_path = backup_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Backup manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())

    errors = []
    for rel_path, expected_hash in manifest.get("hashes", {}).items():
        file_path = backup_path / rel_path
        if not file_path.exists():
            errors.append(f"Missing: {rel_path}")
            continue
        h = __import__("hashlib").sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        if h.hexdigest() != expected_hash:
            errors.append(f"Hash mismatch: {rel_path}")

    return {
        "backup_id": manifest.get("backup_id"),
        "timestamp": manifest.get("timestamp"),
        "verified": len(errors) == 0,
        "errors": errors,
        "files_checked": len(manifest.get("hashes", {})),
    }


def restore_backup(backup_id: str, dry_run: bool = False) -> dict[str, Any]:
    backup_path = BACKUP_DIR / backup_id
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    verification = verify_backup(backup_path)
    if not verification["verified"]:
        raise ValueError(f"Backup integrity check failed: {verification['errors']}")

    manifest = json.loads((backup_path / "manifest.json").read_text())
    result = {
        "backup_id": backup_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dry_run": dry_run,
        "restored": [],
        "skipped": [],
    }

    for rel_path in manifest.get("files", []):
        src = backup_path / rel_path
        if not src.exists():
            result["skipped"].append(rel_path)
            continue
        if src.is_dir():
            dest = REPO_ROOT / rel_path
        else:
            dest = REPO_ROOT / rel_path
        if dry_run:
            result["restored"].append(f"[dry-run] {rel_path}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)
            result["restored"].append(rel_path)

    return result


def restore_database(dump_file: Path) -> None:
    if not dump_file.exists():
        raise FileNotFoundError(f"Database dump not found: {dump_file}")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise OSError("DATABASE_URL not set")
    _run_cmd(f"psql {db_url} -f {dump_file}")
    print(f"[restore] Database restored from {dump_file}")


def list_backups() -> list[dict[str, Any]]:
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
    parser = argparse.ArgumentParser(description="Phase 15 Restore Script")
    parser.add_argument("--backup-id", required=True, help="Backup ID to restore")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be restored")
    parser.add_argument("--database-dump", help="Database dump file to restore")
    parser.add_argument("--list", action="store_true", help="List available backups")
    args = parser.parse_args()

    if args.list:
        backups = list_backups()
        for b in backups:
            print(f"{b['backup_id']}: {len(b.get('files', []))} files")
        return

    if args.database_dump:
        restore_database(Path(args.database_dump))
        return

    result = restore_backup(args.backup_id, args.dry_run)
    log_path = BACKUP_DIR / f"restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    log_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"Restore result saved to {log_path}")
    print(f"Restored: {result['restored']}")
    if result["skipped"]:
        print(f"Skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
