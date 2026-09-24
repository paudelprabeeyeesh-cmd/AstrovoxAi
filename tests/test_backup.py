import os
from pathlib import Path

import pytest

from storage.backup import (
    backup_directory,
    backup_file,
    restore_directory,
    restore_file,
    rotate_backups,
)


def test_backup_file_creates_copy(tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_text("hello")
    backup_dir = tmp_path / "backups"
    result = backup_file(source, backup_dir, max_backups=5)
    assert result.exists()
    assert result.read_text() == "hello"
    assert result.parent == backup_dir


def test_backup_file_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        backup_file(tmp_path / "missing.txt", tmp_path / "backups")


def test_backup_file_rejects_directories(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        backup_file(tmp_path, tmp_path / "backups")


def test_rotate_backups_removes_oldest(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for i in range(7):
        p = backup_dir / f"old_{i}.txt"
        p.write_text(str(i))
        os.utime(p, (1000 + i, 1000 + i))
    rotate_backups(backup_dir, max_backups=3)
    remaining = sorted(backup_dir.iterdir())
    assert len(remaining) == 3
    names = [p.name for p in remaining]
    assert "old_6.txt" in names
    assert "old_5.txt" in names
    assert "old_4.txt" in names


def test_backup_directory_creates_archive(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("alpha")
    (source_dir / "b.txt").write_text("beta")
    backup_dir = tmp_path / "backups"
    result = backup_directory(source_dir, backup_dir, max_backups=5)
    assert result.exists()
    assert result.suffixes == [".tar", ".gz"]


def test_backup_directory_missing_source(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        backup_directory(tmp_path / "missing", tmp_path / "backups")


def test_restore_file_copies_back(tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_text("restore me")
    backup_dir = tmp_path / "backups"
    backup_path = backup_file(source, backup_dir)
    target = tmp_path / "restored" / "data.txt"
    restore_file(backup_path, target)
    assert target.exists()
    assert target.read_text() == "restore me"


def test_restore_directory_extracts_archive(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "x.txt").write_text("x-ray")
    backup_dir = tmp_path / "backups"
    archive = backup_directory(source_dir, backup_dir)
    target_dir = tmp_path / "out"
    restore_directory(archive, target_dir)
    assert (target_dir / "x.txt").exists()
    assert (target_dir / "x.txt").read_text() == "x-ray"
