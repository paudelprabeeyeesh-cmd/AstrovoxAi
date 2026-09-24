import os
import tarfile

import pytest

from storage.restore import restore_snapshot


def test_restore_snapshot(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("hello")

    archive = tmp_path / "out.tar.gz"
    import shutil

    shutil.make_archive(str(tmp_path / "out"), "gztar", str(src))

    target = tmp_path / "restored"
    restore_snapshot(tmp_path / "out.tar.gz", target)
    assert (target / "file.txt").read_text() == "hello"


def test_restore_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        restore_snapshot(tmp_path / "missing.tar.gz", tmp_path / "out")
