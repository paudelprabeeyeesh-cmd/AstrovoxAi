from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.model_registry import router as model_registry_router
from app.auth import require_admin, require_verified_email


def _mock_user():
    return "test-user-123"


def _mock_admin():
    return "admin-user-123"


def test_dropdown_models():
    app = FastAPI()
    app.include_router(model_registry_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_verified_email] = _mock_user
    client = TestClient(app)

    response = client.get("/models/dropdown")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]
    assert "source" in data[0]


def test_list_registered_models():
    app = FastAPI()
    app.include_router(model_registry_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_admin] = _mock_admin
    client = TestClient(app)

    response = client.get("/models/registry")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_register_model():
    app = FastAPI()
    app.include_router(model_registry_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_admin] = _mock_admin
    client = TestClient(app)

    response = client.post("/models/registry", json={
        "name": "CustomModel",
        "version": "v1",
        "provider": "openai",
        "model_id": "custom-model-v1",
        "stage": "staging",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CustomModel"
    assert data["stage"] == "staging"


def test_promote_model():
    app = FastAPI()
    app.include_router(model_registry_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_admin] = _mock_admin
    client = TestClient(app)

    create = client.post("/models/registry", json={
        "name": "CustomModel",
        "version": "v1",
        "provider": "openai",
        "model_id": "custom-model-v1",
    })
    assert create.status_code == 200
    entry_id = create.json()["id"]

    response = client.post(f"/models/registry/{entry_id}/promote", data={"stage": "production"})
    assert response.status_code == 200
    assert response.json()["stage"] == "production"


def test_promote_invalid_stage():
    app = FastAPI()
    app.include_router(model_registry_router)
    app.dependency_overrides = {}
    app.dependency_overrides[require_admin] = _mock_admin
    client = TestClient(app)

    response = client.post("/models/registry/fake-id/promote", data={"stage": "invalid"})
    assert response.status_code == 400
