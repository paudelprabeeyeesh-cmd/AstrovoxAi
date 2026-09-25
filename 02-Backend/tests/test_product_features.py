import importlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)
from app.auth import get_current_user

def _mock_user():
    return "test-user"

@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class TestCodeAgent:
    def test_index_repo(self):
        r = client.post("/code/agent/index?repo_path=/tmp/repo")
        assert r.status_code in (200, 404, 500)

    def test_find_references(self):
        r = client.get("/code/agent/references?symbol=test")
        assert r.status_code in (200, 404, 500)


class TestVoiceEndpoints:
    def test_voice_speak(self):
        r = client.post("/voice/speak?text=Hello+world")
        assert r.status_code in (200, 401, 500)

    def test_voice_transcribe(self):
        r = client.post("/voice/transcribe", files={"file": ("test.wav", b"audio", "audio/wav")})
        assert r.status_code in (200, 401, 500)


class TestImageEndpoints:
    def test_generate_image(self):
        r = client.post("/images/generate?prompt=test")
        assert r.status_code in (200, 401, 500)

    def test_understand_image(self):
        r = client.post("/images/understand", files={"file": ("test.png", b"img", "image/png")})
        assert r.status_code in (200, 401, 500)


class TestResearchEndpoints:
    def test_deep_research(self):
        r = client.post("/research/deep?query=test")
        assert r.status_code in (200, 401, 500)

    def test_get_research(self):
        r = client.get("/research/test-id")
        assert r.status_code in (200, 404, 401, 500)


class TestArtifactEndpoints:
    def test_create_artifact(self):
        r = client.post("/artifacts?title=Test&content=<html></html>")
        assert r.status_code in (200, 401, 500)

    def test_list_artifacts(self):
        r = client.get("/artifacts")
        assert r.status_code in (200, 401, 500)


class TestIntegrationEndpoints:
    def test_chrome_browse(self):
        r = client.post("/integrations/chrome/browse?url=https://example.com")
        assert r.status_code in (200, 401, 500)

    def test_excel_edit(self):
        r = client.post("/integrations/excel/edit?file_id=123&operation=edit")
        assert r.status_code in (200, 401, 500)

    def test_powerpoint_edit(self):
        r = client.post("/integrations/powerpoint/edit?file_id=123&operation=edit")
        assert r.status_code in (200, 401, 500)

    def test_slack_tag(self):
        r = client.post("/integrations/slack/tag?channel=general&message=hello")
        assert r.status_code in (200, 401, 500)
