import os
import subprocess
import sys

import pytest


def test_backup_script_runs():
    result = subprocess.run(
        [sys.executable, "scripts/backup_db.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Backup script failed: {result.stdout}\n{result.stderr}"
    backup_dir = os.environ.get("BACKUP_DIR", "/tmp/backups")
    files = os.listdir(backup_dir)
    assert any(f.startswith("astrovox_backup_") for f in files), "No backup file created"


def test_backup_verifier_runs():
    backup_dir = os.environ.get("BACKUP_DIR", "/tmp/backups")
    files = os.listdir(backup_dir)
    backup_file = None
    for f in files:
        if f.startswith("astrovox_backup_"):
            backup_file = os.path.join(backup_dir, f)
            break

    assert backup_file is not None, "No backup file found to verify"
    result = subprocess.run(
        [sys.executable, "scripts/backup_verifier.py", backup_file],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Backup verifier failed: {result.stdout}\n{result.stderr}"


def test_backup_and_restore_script():
    result = subprocess.run(
        [sys.executable, "scripts/backup_db.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Backup script failed: {result.stdout}\n{result.stderr}"


def test_restore_db_help():
    result = subprocess.run(
        [sys.executable, "scripts/restore_db.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "Restore script should exit with error when no backup provided"
    assert "Usage" in result.stdout or "Usage" in result.stderr, "Restore script should show usage"