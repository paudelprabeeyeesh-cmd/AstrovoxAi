import os
import sys
import tempfile
from pathlib import Path

import pytest

from sandboxing.filesystem_jail import FilesystemJail


@pytest.fixture()
def jail(tmp_path):
    return FilesystemJail(root=str(tmp_path))


def test_reject_traversal_double_dot(jail):
    with pytest.raises(ValueError, match="path traversal detected"):
        jail.reject_traversal("etc/../../etc/passwd")


@pytest.mark.skipif(sys.platform == "win32", reason="backslash as literal path char is OS-dependent")
def test_reject_traversal_backslash(jail):
    with pytest.raises(ValueError, match="backslash traversal detected"):
        jail.reject_traversal("etc\\passwd")


def test_resolve_path_under_root(jail):
    resolved = jail.resolve_path("hello.txt")
    assert resolved.startswith(jail.root)


def test_resolve_path_escapes_jail(jail):
    with pytest.raises(ValueError, match="path traversal detected"):
        jail.resolve_path("..")


def test_validate_symlink_escape(jail, tmp_path):
    outside_dir = tempfile.mkdtemp()
    target = str(Path(outside_dir) / "real.txt")
    with pytest.raises(PermissionError, match="symlink escape detected"):
        jail.validate_symlink("link.txt", target)


def test_validate_symlink_outside_jail(jail, tmp_path):
    outside_dir = tempfile.mkdtemp()
    link_path = str(Path(outside_dir) / "jail_link.txt")
    Path(outside_dir).mkdir(parents=True, exist_ok=True)
    with pytest.raises(PermissionError, match="symlink location outside jail"):
        jail.validate_symlink(link_path, os.path.join(jail.root, "real.txt"))


def test_init_creates_root(tmp_path):
    root = tmp_path / "new_jail"
    FilesystemJail(root=str(root))
    assert root.exists()


def test_reject_traversal_ok(jail):
    jail.reject_traversal("hello/world.txt")
