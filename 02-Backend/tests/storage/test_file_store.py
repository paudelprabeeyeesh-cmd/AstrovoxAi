import os
from io import BytesIO

import pytest

from storage.file_store import FileStore


@pytest.fixture
def tmp_store(tmp_path):
    return FileStore(tmp_path)


def test_put_and_get_bytes(tmp_store):
    path = tmp_store.put("file1", b"hello world")
    assert path.exists()
    assert tmp_store.get("file1") == b"hello world"


def test_put_and_get_fileobj(tmp_store):
    bio = BytesIO(b"fileobj content")
    tmp_store.put("file2", bio)
    assert tmp_store.get("file2") == b"fileobj content"


def test_exists(tmp_store):
    assert not tmp_store.exists("missing")
    tmp_store.put("exists", b"data")
    assert tmp_store.exists("exists")


def test_delete(tmp_store):
    tmp_store.put("del", b"x")
    assert tmp_store.exists("del")
    tmp_store.delete("del")
    assert not tmp_store.exists("del")


def test_delete_missing_noop(tmp_store):
    tmp_store.delete("missing")  # should not raise


def test_size(tmp_store):
    tmp_store.put("s", b"abcd")
    assert tmp_store.size("s") == 4
    with pytest.raises(FileNotFoundError):
        tmp_store.size("missing")


def test_checksum(tmp_store):
    tmp_store.put("c", b"abc")
    cksum = tmp_store.checksum("c")
    assert isinstance(cksum, str)
    assert len(cksum) == 64
    with pytest.raises(FileNotFoundError):
        tmp_store.checksum("missing")


def test_key_sanitization(tmp_store):
    tmp_store.put("../weird/path", b"ok")
    assert tmp_store.exists("../weird/path")
