from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.finetuning import router as finetuning_router


def _mock_user():
    return "test-user-123"


def test_create_finetuning_job():
    app = FastAPI()
    app.include_router(finetuning_router)
    app.dependency_overrides = {}
    from app.auth import require_verified_email
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    response = client.post("/finetuning/jobs", json={
        "model": "gpt-4o-mini",
        "training_file": "file-abc123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "id" in data


def test_list_finetuning_jobs():
    app = FastAPI()
    app.include_router(finetuning_router)
    from app.auth import require_verified_email
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    response = client.get("/finetuning/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_finetuning_job_not_found():
    app = FastAPI()
    app.include_router(finetuning_router)
    from app.auth import require_verified_email
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    response = client.get("/finetuning/jobs/nonexistent")
    assert response.status_code == 404


def test_deploy_requires_completed():
    app = FastAPI()
    app.include_router(finetuning_router)
    from app.auth import require_verified_email
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    response = client.post("/finetuning/jobs/nonexistent/deploy")
    assert response.status_code == 404
