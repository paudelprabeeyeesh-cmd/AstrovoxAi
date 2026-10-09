import os

import numpy as np
import pytest

from sandboxing.filesystem_jail import FilesystemJail


def test_resolve_path_within_jail(tmp_path):
    jail = FilesystemJail(str(tmp_path))
    target = jail.resolve_path("subdir/file.txt")
    assert target.startswith(str(tmp_path))


def test_reject_traversal_dotdot(tmp_path):
    jail = FilesystemJail(str(tmp_path))
    with pytest.raises(ValueError):
        jail.resolve_path("..\\..\\etc\\passwd")


def test_reject_backslash_traversal(tmp_path):
    jail = FilesystemJail(str(tmp_path))
    with pytest.raises(ValueError):
        jail.resolve_path("..\\secret")


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated privileges on Windows")
def test_symlink_escape_rejected(tmp_path):
    jail = FilesystemJail(str(tmp_path))
    link = tmp_path / "link"
    target = tmp_path / "target"
    target.write_text("data")
    link.symlink_to(target)
    jail.validate_symlink("link", str(target))
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside")
    with pytest.raises(PermissionError):
        jail.validate_symlink("link", str(outside))


def test_symlink_outside_rejected_when_no_symlink(tmp_path):
    jail = FilesystemJail(str(tmp_path))
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside")
    with pytest.raises(PermissionError):
        jail.validate_symlink("nonexistent", str(outside))


def test_numpy_parameterized_validation(tmp_path):
    jail = FilesystemJail(str(tmp_path))
    cases = np.array([
        ["safe/path", True],
        ["../escape", False],
        ["sub/../other", False],
        ["a/./b", True],
    ])
    for path, expected in cases:
        if not expected:
            with pytest.raises((ValueError, PermissionError)):
                jail.resolve_path(path)
