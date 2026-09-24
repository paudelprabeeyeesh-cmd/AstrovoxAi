"""
Tests for product_polish.artifacts

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.artifacts import Artifact, Artifacts  # noqa: E402


@pytest.fixture()
def store():
    return Artifacts()


class TestArtifactDataclass:
    def test_default_created_at_set(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c")
        assert a.created_at != ""

    def test_created_at_iso_format(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c")
        assert "T" in a.created_at

    def test_default_artifact_type_html(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c")
        assert a.artifact_type == "html"

    def test_custom_artifact_type(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c", artifact_type="code")
        assert a.artifact_type == "code"

    def test_to_dict_contains_keys(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c")
        d = a.to_dict()
        for key in ("id", "title", "content", "artifact_type", "created_at", "meta"):
            assert key in d

    def test_custom_created_at_preserved(self):
        import uuid
        ts = "2024-01-01T00:00:00+00:00"
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c", created_at=ts)
        assert a.created_at == ts

    def test_title_truncation(self):
        import uuid
        long_title = "x" * 500
        a = Artifact(id=str(uuid.uuid4()), title=long_title, content="c")
        assert len(a.title) <= 200

    def test_content_truncation(self):
        import uuid
        long_content = "x" * 2_000_000
        a = Artifact(id=str(uuid.uuid4()), title="t", content=long_content)
        assert len(a.content) <= 1_000_000

    def test_meta_empty_by_default(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c")
        assert a.meta == {}

    def test_meta_stored(self):
        import uuid
        a = Artifact(id=str(uuid.uuid4()), title="t", content="c", meta={"key": "v"})
        assert a.meta["key"] == "v"


class TestArtifactsCreate:
    def test_create_returns_artifact(self, store):
        a = store.create("My Title", "<h1>hello</h1>")
        assert isinstance(a, Artifact)

    def test_create_assigns_id(self, store):
        a = store.create("t", "c")
        assert a.id != ""

    def test_create_sets_title(self, store):
        a = store.create("My Title", "c")
        assert a.title == "My Title"

    def test_create_sets_content(self, store):
        a = store.create("t", "<h1>hello</h1>")
        assert a.content == "<h1>hello</h1>"

    def test_create_sets_default_type(self, store):
        a = store.create("t", "c")
        assert a.artifact_type == "html"

    def test_create_accepts_custom_type(self, store):
        a = store.create("t", "c", artifact_type="code")
        assert a.artifact_type == "code"

    def test_create_title_truncated(self, store):
        a = store.create("x" * 500, "c")
        assert len(a.title) <= 200

    def test_create_content_truncated(self, store):
        a = store.create("t", "x" * 2_000_000)
        assert len(a.content) <= 1_000_000

    def test_create_stores_in_internal_dict(self, store):
        a = store.create("t", "c")
        assert a.id in store._artifacts


class TestArtifactsGet:
    def test_get_existing(self, store):
        a = store.create("t", "c")
        got = store.get(a.id)
        assert got is not None
        assert got.id == a.id

    def test_get_missing_returns_none(self, store):
        assert store.get("nonexistent-id") is None


class TestArtifactsList:
    def test_list_empty_initially(self, store):
        assert store.list_artifacts() == []

    def test_list_after_create(self, store):
        store.create("t", "c")
        assert len(store.list_artifacts()) == 1

    def test_list_respects_limit(self, store):
        for i in range(60):
            store.create(f"t{i}", "c")
        assert len(store.list_artifacts()) <= 50

    def test_list_newest_first(self, store):
        import time
        store.create("old", "c")
        time.sleep(0.02)
        store.create("new", "c")
        items = store.list_artifacts()
        assert items[0].title == "new"
        assert items[1].title == "old"


class TestArtifactsDelete:
    def test_delete_existing_returns_true(self, store):
        a = store.create("t", "c")
        assert store.delete(a.id) is True

    def test_delete_removes_from_store(self, store):
        a = store.create("t", "c")
        store.delete(a.id)
        assert store.get(a.id) is None

    def test_delete_missing_returns_False(self, store):
        assert store.delete("nonexistent") is False


class TestArtifactsThreadSafety:
    def test_concurrent_creates(self, store):
        import threading
        ids = []

        def creator():
            for i in range(20):
                a = store.create(f"t{i}", "c")
                ids.append(a.id)

        threads = [threading.Thread(target=creator) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(set(ids)) == 80
