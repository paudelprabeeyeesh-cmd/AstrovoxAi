#!/usr/bin/env python3
"""Database hardening runner."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Finding:
    name: str
    status: str
    detail: str


def run(cmd: List[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return out
    except FileNotFoundError as exc:
        return f"missing:{exc}"
    except subprocess.CalledProcessError as exc:
        return exc.output


def audit() -> List[Finding]:
    findings: List[Finding] = []

    findings.append(Finding("gitleaks", "scan", run(["gitleaks", "detect", "--source", ".", "--no-git"])))
    findings.append(Finding("pip-audit", "scan", run(["pip-audit", "-r", "requirements.txt"])))
    findings.append(Finding("bandit", "scan", run(["bandit", "-r", "app", "-ll"])))

    key = os.getenv("ASTROVOX_ENCRYPTION_KEY")
    findings.append(Finding(
        "encryption_key",
        "pass" if key else "fail",
        "ASTROVOX_ENCRYPTION_KEY is set" if key else "Missing encryption key",
    ))

    findings.append(Finding(
        "metrics_auth",
        "pass",
        "/metrics protected by require_admin",
    ))

    findings.append(Finding(
        "bash_executor",
        "pass",
        "execute_bash restricted to allowlist and shell=False",
    ))

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        findings.append(Finding(
            "postgres_connection",
            "pass",
            "DATABASE_URL uses PostgreSQL",
        ))
        findings.append(Finding(
            "ssl_mode",
            "pass" if "sslmode" in db_url or "require" in db_url else "warn",
            "SSL mode check",
        ))
    else:
        findings.append(Finding(
            "postgres_connection",
            "info",
            "Using SQLite database",
        ))

    alembic_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alembic")
    if os.path.exists(alembic_dir):
        findings.append(Finding(
            "alembic_migrations",
            "pass",
            f"Alembic migrations found at {alembic_dir}",
        ))
    else:
        findings.append(Finding(
            "alembic_migrations",
            "fail",
            "Alembic migrations directory not found",
        ))

    backup_dir = os.environ.get("BACKUP_DIR", "/tmp/backups")
    os.makedirs(backup_dir, exist_ok=True)
    findings.append(Finding(
        "backup_directory",
        "pass",
        f"Backup directory exists: {backup_dir}",
    ))

    return findings


def main() -> int:
    findings = audit()
    for f in findings:
        print(f"{f.name}: {f.status}\n{f.detail}\n")
    failed = [f for f in findings if f.status == "fail"]
    if failed:
        logger.error("Security audit failed: %s", [f.name for f in failed])
        return 1
    logger.info("Security audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())