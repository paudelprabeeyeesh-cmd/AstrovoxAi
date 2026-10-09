from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.training import router as training_router
from app.auth import require_admin, require_verified_email


def _mock_user():
    return "test-user-123"


def _mock_admin():
    return "admin-user-123"


def test_upload_training_dataset():
    app = FastAPI()
    app.include_router(training_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_admin] = _mock_admin
    client = TestClient(app)

    response = client.post(
        "/training/upload",
        data={"name": "test-dataset"},
        files={"file": ("test.jsonl", b'{"prompt":"hello","response":"world"}\n', "application/jsonl")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-dataset"
    assert data["status"] == "uploaded"


def test_list_training_datasets():
    app = FastAPI()
    app.include_router(training_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_admin] = _mock_admin
    client = TestClient(app)

    response = client.get("/training/datasets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_training_job():
    app = FastAPI()
    app.include_router(training_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    response = client.post("/training/jobs", json={
        "model": "gpt-4o-mini",
        "training_file": "file-abc123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "id" in data


def test_start_training_job():
    app = FastAPI()
    app.include_router(training_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    create = client.post("/training/jobs", json={
        "model": "gpt-4o-mini",
        "training_file": "file-abc123",
    })
    assert create.status_code == 200
    job_id = create.json()["id"]

    response = client.post(f"/training/jobs/{job_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "training"


def test_complete_training_job():
    app = FastAPI()
    app.include_router(training_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    create = client.post("/training/jobs", json={
        "model": "gpt-4o-mini",
        "training_file": "file-abc123",
    })
    assert create.status_code == 200
    job_id = create.json()["id"]

    client.post(f"/training/jobs/{job_id}/start")
    response = client.post(f"/training/jobs/{job_id}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "fine_tuned_model" in response.json()
