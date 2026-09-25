import uuid
from unittest.mock import patch, MagicMock

import pytest
from app.compliance import delete_user_data, export_user_data, record_consent


@pytest.fixture(autouse=True)
def _mock_db():
    with patch("app.compliance.get_db") as mock_get_db:
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.commit.return_value = None
        yield mock_conn


def test_gdpr_delete_user(_mock_db):
    user_id = str(uuid.uuid4())
    delete_user_data(user_id)
    executed = [call[0][0].strip().upper() for call in _mock_db.execute.call_args_list]
    deletes = [sql for sql in executed if sql.startswith("DELETE FROM")]
    assert any("DELETE FROM users WHERE id = ?".upper() == sql for sql in deletes)
    assert any("DELETE FROM refresh_tokens WHERE user_id = ?".upper() == sql for sql in deletes)
    assert any("DELETE FROM memories WHERE user_id = ?".upper() == sql for sql in deletes)
    assert any("DELETE FROM conversations WHERE user_id = ?".upper() == sql for sql in deletes)
    assert any("DELETE FROM usage WHERE user_id = ?".upper() == sql for sql in deletes)
    assert any("DELETE FROM subscriptions WHERE user_id = ?".upper() == sql for sql in deletes)
    assert any("DELETE FROM audit_logs WHERE user_id = ?".upper() == sql for sql in deletes)
    assert _mock_db.commit.call_count >= 1


def test_gdpr_export_user(_mock_db):
    user_id = str(uuid.uuid4())
    _mock_db.execute.return_value.fetchall.return_value = []
    data = export_user_data(user_id)
    assert data["user_id"] == user_id
    assert "users" in data
    assert "memories" in data
    assert "conversations" in data
    assert "messages" in data
    assert "consent_records" in data
    assert "audit_logs" in data
    assert _mock_db.execute.call_count >= 1


def test_consent_recording(_mock_db):
    user_id = str(uuid.uuid4())
    result = record_consent(user_id, "marketing", True)
    assert result["recorded"] is True
    sql = _mock_db.execute.call_args[0][0]
    assert "INSERT INTO consent_records" in sql
    assert user_id in _mock_db.execute.call_args[0][1]
    assert "marketing" in _mock_db.execute.call_args[0][1]
    assert _mock_db.commit.call_count == 2
