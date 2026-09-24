from product_polish.projects import Project, ProjectFile, Projects


def test_project_auto_created_at():
    project = Project(id="1", name="p")
    assert project.created_at != ""


def test_project_to_dict():
    project = Project(id="1", name="p", instructions="i", meta={"k": 1})
    d = project.to_dict()
    assert d["id"] == "1"
    assert d["meta"] == {"k": 1}


def test_project_file_auto_created_at():
    pf = ProjectFile(id="1", project_id="p1", filename="f.py", content="c")
    assert pf.created_at != ""


def test_project_file_to_dict():
    pf = ProjectFile(id="1", project_id="p1", filename="f.py", content="c")
    d = pf.to_dict()
    assert d["project_id"] == "p1"
    assert d["content"] == "c"


def test_projects_create_and_get():
    projects = Projects()
    project = projects.create("My Project", instructions="Do stuff")
    assert project.id is not None
    fetched = projects.get(project.id)
    assert fetched is project


def test_projects_list_sorted_desc():
    projects = Projects()
    p1 = projects.create("A")
    p2 = projects.create("B")
    items = projects.list_projects()
    assert items[0].id == p2.id


def test_projects_delete():
    projects = Projects()
    project = projects.create("p")
    assert projects.delete(project.id) is True
    assert projects.get(project.id) is None
    assert projects.delete(project.id) is False


def test_add_file_returns_none_for_missing_project():
    projects = Projects()
    assert projects.add_file("missing", "f.py", "c") is None


def test_add_file_and_list_files():
    projects = Projects()
    project = projects.create("p")
    pf = projects.add_file(project.id, "f.py", "print(1)")
    assert pf is not None
    files = projects.list_files(project.id)
    assert len(files) == 1
    assert files[0].filename == "f.py"


def test_list_files_for_missing_project():
    projects = Projects()
    assert projects.list_files("missing") == []
