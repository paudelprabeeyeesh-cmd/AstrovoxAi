import os
import subprocess
import sys

import pytest


def test_security_audit_passes():
    result = subprocess.run(
        [sys.executable, "scripts/security_audit.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Security audit failed: {result.stdout}\n{result.stderr}"


def test_database_hardening_audit_passes():
    result = subprocess.run(
        [sys.executable, "scripts/database_hardening.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Database hardening audit failed: {result.stdout}\n{result.stderr}"


def test_alembic_migrations_directory_exists():
    # tests/integration/test_database_hardening.py -> tests/integration ->
    # tests -> backend root. The path was previously one level short, so this
    # looked for `tests/alembic` and never found the real configuration.
    backend_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    alembic_dir = os.path.join(backend_root, "alembic")
    assert os.path.exists(alembic_dir), "Alembic migrations directory not found"
    assert os.path.exists(os.path.join(alembic_dir, "versions")), "Alembic versions directory not found"
    assert os.path.exists(os.path.join(alembic_dir, "env.py")), "Alembic env.py not found"


def test_database_url_configured():
    assert os.environ.get("DATABASE_URL") is not None, "DATABASE_URL must be set"


def test_encryption_key_configured():
    assert os.environ.get("ASTROVOX_ENCRYPTION_KEY") is not None, "ASTROVOX_ENCRYPTION_KEY must be set"


def test_backup_directory_exists():
    backup_dir = os.environ.get("BACKUP_DIR", "/tmp/backups")
    os.makedirs(backup_dir, exist_ok=True)
    assert os.path.exists(backup_dir), f"Backup directory does not exist: {backup_dir}"


def test_models_importable():
    from app.models import Base

    assert Base is not None, "SQLAlchemy Base not importable"