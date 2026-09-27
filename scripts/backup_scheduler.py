#!/usr/bin/env python3
"""
Phase 15 Backup Scheduler
Schedule automated backups using cron or APScheduler.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_CONFIG = REPO_ROOT / "configs" / "backup_schedule.json"


def load_schedule() -> Dict[str, Any]:
    if SCHEDULE_CONFIG.exists():
        return json.loads(SCHEDULE_CONFIG.read_text())
    return {"schedules": []}


def save_schedule(schedule: Dict[str, Any]) -> None:
    SCHEDULE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_CONFIG.write_text(json.dumps(schedule, indent=2, default=str))


def add_schedule(name: str, cron_expression: str, backup_name: Optional[str] = None, include_database: bool = False, include_docker: bool = False) -> Dict[str, Any]:
    schedule = load_schedule()
    entry = {
        "name": name,
        "cron": cron_expression,
        "backup_name": backup_name or f"scheduled_{name}",
        "include_database": include_database,
        "include_docker": include_docker,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "active": True,
    }
    schedule["schedules"].append(entry)
    save_schedule(schedule)
    return entry


def list_schedules() -> List[Dict[str, Any]]:
    schedule = load_schedule()
    return schedule.get("schedules", [])


def remove_schedule(name: str) -> None:
    schedule = load_schedule()
    schedule["schedules"] = [s for s in schedule.get("schedules", []) if s["name"] != name]
    save_schedule(schedule)


def run_backup(name: Optional[str] = None, include_database: bool = False, include_docker: bool = False) -> int:
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "backup.py")]
    if name:
        cmd.extend(["--name", name])
    if include_database:
        cmd.append("--database")
    if include_docker:
        cmd.append("--docker")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return result.returncode


def install_cron_jobs() -> None:
    if os.name != "posix":
        print("Cron scheduling is only supported on POSIX systems.")
        return
    schedules = list_schedules()
    cron_lines = []
    for entry in schedules:
        if not entry.get("active"):
            continue
        cron_lines.append(f"# AstrovoxAI backup: {entry['name']}")
        cron_lines.append(f"{entry['cron']} {sys.executable} {REPO_ROOT}/scripts/backup.py --name {entry['backup_name']}")
        if entry.get("include_database"):
            cron_lines[-1] += " --database"
        if entry.get("include_docker"):
            cron_lines[-1] += " --docker"
        cron_lines.append("")

    cron_file = REPO_ROOT / "configs" / "backup_cron.txt"
    cron_file.write_text("\n".join(cron_lines))
    print(f"Cron entries written to {cron_file}")
    print("To install:")
    print(f"  crontab {cron_file}")


def main():
    parser = argparse.ArgumentParser(description="Phase 15 Backup Scheduler")
    parser.add_argument("--add", action="append", nargs=2, metavar=("NAME", "CRON"), help="Add a schedule")
    parser.add_argument("--backup-name", help="Backup name prefix")
    parser.add_argument("--include-database", action="store_true", help="Include database in scheduled backup")
    parser.add_argument("--include-docker", action="store_true", help="Include Docker volumes")
    parser.add_argument("--remove", help="Remove schedule by name")
    parser.add_argument("--list", action="store_true", help="List schedules")
    parser.add_argument("--run-now", action="store_true", help="Run backup immediately")
    parser.add_argument("--install-cron", action="store_true", help="Generate cron file")
    args = parser.parse_args()

    if args.add:
        for name, cron in args.add:
            entry = add_schedule(name, cron, args.backup_name, args.include_database, args.include_docker)
            print(f"Added schedule: {entry}")
    if args.remove:
        remove_schedule(args.remove)
        print(f"Removed schedule: {args.remove}")
    if args.list:
        for entry in list_schedules():
            print(json.dumps(entry, indent=2))
    if args.run_now:
        code = run_backup(args.backup_name, args.include_database, args.include_docker)
        sys.exit(code)
    if args.install_cron:
        install_cron_jobs()


if __name__ == "__main__":
    main()
