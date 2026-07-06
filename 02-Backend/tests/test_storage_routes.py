from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_storage_upload_requires_user_id():
    response = client.post(
        "/storage/avatars/upload",
        files={"file": ("avatar.png", b"abc", "image/png")},
        data={"path": "user/test/avatar.png"},
    )
    assert response.status_code == 400
