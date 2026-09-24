from product_polish.artifacts import Artifact, Artifacts


def test_artifact_auto_created_at():
    artifact = Artifact(id="1", title="t", content="c")
    assert artifact.created_at != ""


def test_artifact_title_truncation():
    artifact = Artifact(id="1", title="x" * 300, content="c")
    assert len(artifact.title) == 200


def test_artifact_content_truncation():
    artifact = Artifact(id="1", title="t", content="x" * 2_000_000)
    assert len(artifact.content) == 1_000_000


def test_artifact_to_dict():
    artifact = Artifact(id="1", title="t", content="c", artifact_type="code", meta={"k": 1})
    d = artifact.to_dict()
    assert d["id"] == "1"
    assert d["artifact_type"] == "code"
    assert d["meta"] == {"k": 1}


def test_artifacts_create_and_get():
    store = Artifacts()
    artifact = store.create("title", "content")
    assert artifact.id is not None
    fetched = store.get(artifact.id)
    assert fetched is artifact


def test_artifacts_list_sorted_desc():
    store = Artifacts()
    a1 = store.create("a", "1")
    a2 = store.create("b", "2")
    items = store.list_artifacts()
    assert items[0].id == a2.id


def test_artifacts_delete():
    store = Artifacts()
    artifact = store.create("t", "c")
    assert store.delete(artifact.id) is True
    assert store.get(artifact.id) is None
    assert store.delete(artifact.id) is False


def test_artifacts_max_limit_evicts_oldest():
    store = Artifacts(max_artifacts=2)
    a1 = store.create("a", "1")
    store.create("b", "2")
    store.create("c", "3")
    assert len(store.list_artifacts()) == 2
    assert store.get(a1.id) is None
