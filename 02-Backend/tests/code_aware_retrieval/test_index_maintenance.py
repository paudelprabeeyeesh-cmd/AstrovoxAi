import tempfile

from code_aware_retrieval.index_maintenance import FileEvent, IndexMaintenance


class MockParser:
    def parse(self, path, content):
        return {"path": path, "size": len(content)}


def _make_im():
    return IndexMaintenance(parser=MockParser())


def test_hash_content_deterministic():
    im = _make_im()
    h1 = im._hash_content("f.py", "content")
    h2 = im._hash_content("f.py", "content")
    assert h1 == h2


def test_hash_content_differs():
    im = _make_im()
    assert im._hash_content("a.py", "x") != im._hash_content("b.py", "x")


def test_on_file_event_adds_to_dirty():
    im = _make_im()
    im.on_file_event(FileEvent(path="a.py", event_type="modified"))
    assert "a.py" in im._dirty


def test_on_file_event_stores_hash():
    im = _make_im()
    im.on_file_event(
        FileEvent(path="a.py", event_type="modified", content_hash="abc123")
    )
    assert im._hashes["a.py"] == "abc123"


def test_incremental_reindex_dirty_file():
    im = _make_im()
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write("x=1")
        path = f.name
    im.on_file_event(FileEvent(path=path, event_type="modified", content_hash="old"))
    count = im.incremental_reindex()
    assert count == 1
    assert path in im._index
    assert path in im._hashes


def test_incremental_reindex_not_dirty_skips():
    im = _make_im()
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write("x=1")
        path = f.name
    im.on_file_event(FileEvent(path=path, event_type="modified", content_hash="old"))
    im.incremental_reindex()
    count = im.incremental_reindex()
    assert count == 0


def test_incremental_reindex_nonexistent_file_skips():
    im = _make_im()
    im.on_file_event(
        FileEvent(path="/nonexistent/a.py", event_type="deleted", content_hash="old")
    )
    count = im.incremental_reindex()
    assert count == 0


def test_full_reindex_multiple_files():
    im = _make_im()
    paths = []
    for name in ["a.py", "b.py", "c.py"]:
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(f"{name}=1")
            paths.append(f.name)
    count = im.full_reindex(paths)
    assert count == 3
    for path in paths:
        assert path in im._index
        assert path in im._hashes


def test_full_reindex_clears_dirty():
    im = _make_im()
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write("pass")
        path = f.name
    im._dirty.add("x.py")
    im.full_reindex([path])
    assert len(im._dirty) == 0


def test_consistency_check_consistent():
    im = _make_im()
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write("pass")
        path = f.name
    im.full_reindex([path])
    result = im.consistency_check()
    assert result["consistent"] is True
    assert result["in_index_not_hashed"] == []
    assert result["in_hash_not_indexed"] == []


def test_consistency_check_inconsistent():
    im = _make_im()
    im._index["x.py"] = "parsed"
    result = im.consistency_check()
    assert result["consistent"] is False
    assert "x.py" in result["in_index_not_hashed"]


def test_get_index_stats():
    im = _make_im()
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write("pass")
        path = f.name
    im.full_reindex([path])
    im._dirty.add("dirty.py")
    stats = im.get_index_stats()
    assert stats["total_files"] == 1
    assert stats["dirty_files"] == 1
    assert stats["hashes"] == 1
