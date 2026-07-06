from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_rate_limit_headers_present_on_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
