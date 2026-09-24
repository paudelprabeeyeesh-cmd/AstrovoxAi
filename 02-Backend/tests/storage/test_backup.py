import os

import pytest

from storage.backup import backup_directory, backup_file, rotate_backups


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
