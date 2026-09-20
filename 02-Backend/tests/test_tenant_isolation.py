import uuid
from fastapi.testclient import TestClient
import importlib

client = TestClient(importlib.import_module("app.main").app)


def _create_verified_user(prefix: str):
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"
    password = "testpass123"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    user_id = r.json()["user"]["user_id"]

    from app.auth import create_verification_token
    verification_token = create_verification_token(user_id, email)
    r = client.post("/auth/verify", params={"token": verification_token})
    assert r.status_code == 200, r.text

    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    return user_id, token


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


class TestTenantIsolation:
    def test_memory_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a")
        user_b_id, token_b = _create_verified_user("tenant-b")

        r = client.post("/memory", json={"key": "secret", "value": "data-a"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        memory_id = r.json()["id"]

        r = client.put(f"/memory/{memory_id}", json={"value": "hacked"}, headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/memory/{memory_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.put(f"/memory/{memory_id}", json={"value": "hacked"}, headers=_headers(token_a))
        assert r.status_code == 200

        r = client.delete(f"/memory/{memory_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_template_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-tpl")
        user_b_id, token_b = _create_verified_user("tenant-b-tpl")

        r = client.post("/templates", json={"name": "tpl-a", "prompt": "prompt-a"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        tpl_id = r.json()["id"]

        r = client.put(f"/templates/{tpl_id}", json={"name": "hacked", "prompt": "hacked"}, headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/templates/{tpl_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.put(f"/templates/{tpl_id}", json={"name": "hacked", "prompt": "hacked"}, headers=_headers(token_a))
        assert r.status_code == 200

        r = client.delete(f"/templates/{tpl_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_schedule_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-sched")
        user_b_id, token_b = _create_verified_user("tenant-b-sched")

        r = client.post("/schedules", json={"cron": "0 9 * * *", "email": "a@test.com"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        schedule_id = r.json()["id"]

        r = client.delete(f"/schedules/{schedule_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/schedules/{schedule_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_knowledge_doc_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-doc")
        user_b_id, token_b = _create_verified_user("tenant-b-doc")

        r = client.post("/knowledge", json={"title": "doc-a", "content": "content-a"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        doc_id = r.json()["id"]

        r = client.delete(f"/knowledge/{doc_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/knowledge/{doc_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_workflow_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-wf")
        user_b_id, token_b = _create_verified_user("tenant-b-wf")

        r = client.post("/workflows", json={"name": "wf-a", "steps": "step1"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        wf_id = r.json()["id"]

        r = client.delete(f"/workflows/{wf_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/workflows/{wf_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_tool_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-tool")
        user_b_id, token_b = _create_verified_user("tenant-b-tool")

        r = client.post("/tools", json={"type": "test", "config": "{}"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        tool_id = r.json()["id"]

        r = client.delete(f"/tools/{tool_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/tools/{tool_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_feedback_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-fb")
        user_b_id, token_b = _create_verified_user("tenant-b-fb")

        r = client.post("/feedback", json={"rating": 5, "comment": "great"}, headers=_headers(token_a))
        assert r.status_code == 200, r.text
        fb_id = r.json()["id"]

        r = client.delete(f"/feedback/{fb_id}", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.delete(f"/feedback/{fb_id}", headers=_headers(token_a))
        assert r.status_code == 200

    def test_conversation_message_cross_tenant_access(self):
        user_a_id, token_a = _create_verified_user("tenant-a-conv")
        user_b_id, token_b = _create_verified_user("tenant-b-conv")

        r = client.post("/conversations", headers=_headers(token_a))
        assert r.status_code == 200, r.text
        conv_id = r.json()["id"]

        r = client.get(f"/conversations/{conv_id}/messages", headers=_headers(token_b))
        assert r.status_code == 404

        r = client.get(f"/conversations/{conv_id}/messages", headers=_headers(token_a))
        assert r.status_code == 200
