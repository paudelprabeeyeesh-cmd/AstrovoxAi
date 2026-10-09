"""
Tests for product_polish.projects

Uses only stdlib.
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.projects import Project, ProjectFile, Projects  # noqa: E402


@pytest.fixture()
def project_store():
    return Projects()


class TestProjectDataclass:
    def test_default_created_at_set(self):
        p = Project(id="p1", name="n")
        assert p.created_at != ""

    def test_default_instructions_empty(self):
        p = Project(id="p1", name="n")
        assert p.instructions == ""

    def test_to_dict_contains_keys(self):
        p = Project(id="p1", name="n")
        d = p.to_dict()
        for key in ("id", "name", "instructions", "created_at", "meta"):
            assert key in d

    def test_custom_created_at_preserved(self):
        ts = "2024-01-01T00:00:00+00:00"
        p = Project(id="p1", name="n", created_at=ts)
        assert p.created_at == ts

    def test_default_meta_empty(self):
        p = Project(id="p1", name="n")
        assert p.meta == {}

    def test_meta_stored(self):
        p = Project(id="p1", name="n", meta={"k": "v"})
        assert p.meta["k"] == "v"


class TestProjectFileDataclass:
    def test_default_created_at_set(self):
        import uuid
        pf = ProjectFile(id=str(uuid.uuid4()), project_id="p1", filename="f.txt", content="c")
        assert pf.created_at != ""

    def test_to_dict_contains_keys(self):
        import uuid
        pf = ProjectFile(id=str(uuid.uuid4()), project_id="p1", filename="f.txt", content="c")
        d = pf.to_dict()
        for key in ("id", "project_id", "filename", "content", "created_at"):
            assert key in d

    def test_content_stored(self):
        import uuid
        pf = ProjectFile(id=str(uuid.uuid4()), project_id="p1", filename="f.txt", content="hello")
        assert pf.content == "hello"

    def test_filename_stored(self):
        import uuid
        pf = ProjectFile(id=str(uuid.uuid4()), project_id="p1", filename="main.py", content="")
        assert pf.filename == "main.py"


class TestProjectsCreate:
    def test_create_returns_project(self, project_store):
        p = project_store.create("My Project")
        assert isinstance(p, Project)

    def test_create_assigns_id(self, project_store):
        p = project_store.create("My Project")
        assert p.id != ""

    def test_create_sets_name(self, project_store):
        p = project_store.create("My Project")
        assert p.name == "My Project"

    def test_create_sets_empty_instructions(self, project_store):
        p = project_store.create("My Project")
        assert p.instructions == ""

    def test_create_sets_instructions(self, project_store):
        p = project_store.create("My Project", instructions="do stuff")
        assert p.instructions == "do stuff"

    def test_create_stores_internal(self, project_store):
        p = project_store.create("My Project")
        assert p.id in project_store._projects

    def test_create_stores_empty_files_map(self, project_store):
        p = project_store.create("My Project")
        assert p.id in project_store._files
        assert project_store._files[p.id] == {}

    def test_create_two_returns_distinct_ids(self, project_store):
        p1 = project_store.create("A")
        p2 = project_store.create("B")
        assert p1.id != p2.id


class TestProjectsGet:
    def test_get_existing(self, project_store):
        p = project_store.create("My Project")
        got = project_store.get(p.id)
        assert got is not None
        assert got.name == "My Project"

    def test_get_missing_returns_none(self, project_store):
        assert project_store.get("nonexistent") is None


class TestProjectsList:
    def test_list_empty_initially(self, project_store):
        assert project_store.list_projects() == []

    def test_list_after_create(self, project_store):
        project_store.create("My Project")
        assert len(project_store.list_projects()) == 1

    def test_list_multiple(self, project_store):
        project_store.create("A")
        project_store.create("B")
        assert len(project_store.list_projects()) == 2

    def test_list_newest_first(self, project_store):
        project_store.create("old")
        import time
        time.sleep(0.5)
        project_store.create("new")
        items = project_store.list_projects()
        assert items[0].name == "new"
        assert items[1].name == "old"


class TestProjectsDelete:
    def test_delete_existing_returns_true(self, project_store):
        p = project_store.create("My Project")
        assert project_store.delete(p.id) is True

    def test_delete_removes_project(self, project_store):
        p = project_store.create("My Project")
        project_store.delete(p.id)
        assert project_store.get(p.id) is None

    def test_delete_removes_files_map(self, project_store):
        p = project_store.create("My Project")
        project_store.delete(p.id)
        assert p.id not in project_store._files

    def test_delete_missing_returns_False(self, project_store):
        assert project_store.delete("nonexistent") is False


class TestAddProjectFile:
    def test_add_file_returns_project_file(self, project_store):
        p = project_store.create("P")
        pf = project_store.add_file(p.id, "main.py", "print(1)")
        assert isinstance(pf, ProjectFile)

    def test_add_file_stores_content(self, project_store):
        p = project_store.create("P")
        pf = project_store.add_file(p.id, "main.py", "print(1)")
        assert pf.content == "print(1)"

    def test_add_file_returns_none_missing_project(self, project_store):
        assert project_store.add_file("missing", "f.txt", "c") is None

    def test_add_file_tracks_filename(self, project_store):
        p = project_store.create("P")
        pf = project_store.add_file(p.id, "main.py", "")
        assert pf.filename == "main.py"

    def test_add_multiple_files(self, project_store):
        p = project_store.create("P")
        project_store.add_file(p.id, "a.py", "a")
        project_store.add_file(p.id, "b.py", "b")
        assert len(project_store.list_files(p.id)) == 2

    def test_list_files_empty_no_files(self, project_store):
        p = project_store.create("P")
        assert project_store.list_files(p.id) == []

    def test_list_files_missing_project_empty(self, project_store):
        assert project_store.list_files("missing") == []

    def test_list_files_returns_both(self, project_store):
        p = project_store.create("P")
        project_store.add_file(p.id, "a.py", "a")
        time.sleep(1.1)
        project_store.add_file(p.id, "b.py", "b")
        files = project_store.list_files(p.id)
        assert len(files) == 2
        names = [f.filename for f in files]
        assert "a.py" in names
        assert "b.py" in names


class TestProjectsThreadSafety:
    def test_concurrent_creates(self, project_store):
        import threading
        ids = []

        def creator():
            for _ in range(10):
                p = project_store.create("P")
                ids.append(p.id)

        threads = [threading.Thread(target=creator) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(set(ids)) == 40

    def test_concurrent_add_files(self, project_store):
        import threading
        p = project_store.create("P")
        errors = []

        def adder():
            try:
                for i in range(10):
                    project_store.add_file(p.id, f"f{i}.py", "")
            except Exception as _e:  # noqa: BLE001
                errors.append(_e)

        threads = [threading.Thread(target=adder) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
