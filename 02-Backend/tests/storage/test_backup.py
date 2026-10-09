import os

import pytest

from storage.backup import (
    backup_directory,
    backup_file,
    restore_directory,
    restore_file,
    rotate_backups,
)


def test_rotate_backups_empty(tmp_path):
    rotate_backups(tmp_path, max_backups=2)


def test_rotate_backups_removes_oldest(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}").write_text(str(i))
    rotate_backups(tmp_path, max_backups=2)
    assert len(list(tmp_path.iterdir())) == 2


def test_backup_file_creates_copy(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    out = backup_file(src, tmp_path / "backups", max_backups=5)
    assert out.exists()
    assert out.read_text() == "data"


def test_backup_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_file(tmp_path / "nope.txt", tmp_path / "backups")


def test_backup_file_directory_raises(tmp_path):
    with pytest.raises(ValueError):
        backup_file(tmp_path, tmp_path / "backups")


def test_backup_directory(tmp_path):
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "a.txt").write_text("a")
    out = backup_directory(src, tmp_path / "backups", max_backups=5)
    assert out.exists()
    assert out.suffixes == [".tar", ".gz"]


def test_restore_file_copies_backup(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    backup = backup_file(src, tmp_path / "backups", max_backups=5)
    target = tmp_path / "restored.txt"
    restore_file(backup, target)
    assert target.exists()
    assert target.read_text() == "hello"


def test_restore_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        restore_file(tmp_path / "nope.txt", tmp_path / "out.txt")


def test_restore_directory_extracts_archive(tmp_path):
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "a.txt").write_text("alpha")
    backup = backup_directory(src, tmp_path / "backups", max_backups=5)
    target = tmp_path / "restored_dir"
    restore_directory(backup, target)
    assert (target / "a.txt").exists()
    assert (target / "a.txt").read_text() == "alpha"


def test_restore_directory_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        restore_directory(tmp_path / "nope.tar.gz", tmp_path / "out_dir")


def test_rotate_backups_limits_count(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("x")
    for _ in range(6):
        backup_file(src, tmp_path / "backups", max_backups=3)
    assert len(list((tmp_path / "backups").iterdir())) == 3
