#!/usr/bin/env python3
"""
Phase 15 Production Rollback System
Supports model version rollback, configuration rollback, and service rollback.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO_ROOT / "backups"
ROLLBACK_LOG = BACKUP_DIR / "rollback.log"


def log(msg: str) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.utcnow().isoformat()}] {msg}"
    print(line)
    with open(ROLLBACK_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def rollback_model(name: str, target_version: str) -> dict[str, Any]:
    log(f"Rolling back model {name} to {target_version}")
    sys.path.insert(0, str(REPO_ROOT))
    from models.registry.registry import get_model, update_model_status

    current = get_model(name)
    target = get_model(name, target_version)

    source = REPO_ROOT / target["file"]
    dest = REPO_ROOT / current["file"]
    if source.exists():
        shutil.copy2(source, dest)
        log(f"Copied {source} -> {dest}")

    update_model_status(name, target_version, "deployed")
    if current["version"] != target_version:
        update_model_status(name, current["version"], "rolled_back")

    return {
        "action": "rollback_model",
        "name": name,
        "from_version": current["version"],
        "to_version": target_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def rollback_config(config_name: str, backup_path: str) -> dict[str, Any]:
    log(f"Rolling back config {config_name} from {backup_path}")
    config_dir = REPO_ROOT / "configs" / "versioned"
    backup_file = Path(backup_path)
    if not backup_file.exists():
        backup_file = BACKUP_DIR / backup_path

    if not backup_file.exists():
        raise FileNotFoundError(f"Config backup not found: {backup_path}")

    dest = config_dir / config_name
    shutil.copy2(backup_file, dest)
    log(f"Restored config from {backup_file} -> {dest}")
    return {
        "action": "rollback_config",
        "config": config_name,
        "from_backup": str(backup_file),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def rollback_service(service_name: str, previous_task_definition: str) -> dict[str, Any]:
    log(f"Rolling back service {service_name} to task {previous_task_definition}")
    run_cmd = lambda cmd: subprocess.run(cmd, check=True, capture_output=True, text=True)
    try:
        run_cmd([
            "aws", "ecs", "update-service",
            "--cluster", "astrovox-production",
            "--service", service_name,
            "--task-definition", previous_task_definition,
        ])
    except Exception as e:
        log(f"Service rollback failed: {e}")
        raise
    return {
        "action": "rollback_service",
        "service": service_name,
        "task_definition": previous_task_definition,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def list_model_versions(name: str) -> list[str]:
    sys.path.insert(0, str(REPO_ROOT))
    from models.registry.registry import get_model
    model = get_model(name)
    return sorted(model.get("versions", {}).keys())


def list_config_backups() -> list[str]:
    if not BACKUP_DIR.exists():
        return []
    return sorted([p.name for p in BACKUP_DIR.glob("config_*.yaml")])


def main():
    parser = argparse.ArgumentParser(description="Phase 15 Rollback System")
    parser.add_argument("--model", help="Model name to rollback")
    parser.add_argument("--model-version", help="Target model version")
    parser.add_argument("--config", help="Config filename to rollback")
    parser.add_argument("--config-backup", help="Config backup path")
    parser.add_argument("--service", help="Service name to rollback")
    parser.add_argument("--task-definition", help="Previous task definition ARN")
    parser.add_argument("--list-model-versions", help="List versions for a model")
    parser.add_argument("--list-config-backups", action="store_true", help="List config backups")
    args = parser.parse_args()

    if args.list_model_versions:
        versions = list_model_versions(args.list_model_versions)
        print(f"Versions for {args.list_model_versions}: {versions}")
        return
    if args.list_config_backups:
        backups = list_config_backups()
        print(f"Config backups: {backups}")
        return

    result = None
    if args.model and args.model_version:
        result = rollback_model(args.model, args.model_version)
    elif args.config and args.config_backup:
        result = rollback_config(args.config, args.config_backup)
    elif args.service and args.task_definition:
        result = rollback_service(args.service, args.task_definition)
    else:
        parser.print_help()
        sys.exit(1)

    if result:
        log_path = BACKUP_DIR / f"rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        log_path.write_text(json.dumps(result, indent=2, default=str))
        print(f"Rollback result saved to {log_path}")


if __name__ == "__main__":
    main()
