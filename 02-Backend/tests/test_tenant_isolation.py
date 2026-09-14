import uuid
from unittest.mock import patch, MagicMock

_mock_conn = MagicMock()
_mock_cur = _mock_conn.cursor.return_value
_mock_cur.lastrowid = uuid.uuid4().hex

_mock_db = MagicMock()
_mock_db.__enter__ = MagicMock(return_value=_mock_conn)
_mock_db.__exit__ = MagicMock(return_value=False)


def _create_verified_user(prefix: str):
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"
    user_id = str(uuid.uuid4())
    with patch("app.database.get_db") as mock_get_db:
        mock_get_db.return_value = _mock_db
        conn = mock_get_db().__enter__.return_value
        cur = conn.cursor.return_value
        cur.execute(
            "INSERT INTO users (id, email, password_hash, email_verified) VALUES (%s, %s, %s, %s)",
            (user_id, email, "hashed", 1),
        )
        conn.commit.return_value = None
    from app.auth import create_access_token
    token = create_access_token(user_id, email)
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
