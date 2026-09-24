import time
from unittest.mock import MagicMock

import pytest

from sandboxing.approval_store import approval_store, PendingApproval


@pytest.fixture(autouse=True)
def reset_approval_store():
    approval_store._store.clear()
    approval_store._history.clear()
    yield
    approval_store._store.clear()
    approval_store._history.clear()


def test_create_approval():
    approval = approval_store.create(
        tool_name="file_write",
        arguments={"file_path": "/tmp/x", "content": "y"},
        user_id="user-1",
        tier="write",
        operation="file_write file_path=/tmp/x",
        ttl_seconds=300,
    )
    assert approval.approval_id is not None
    assert approval.status == "pending"


def test_get_approval():
    approval = approval_store.create(
        tool_name="file_write",
        arguments={"file_path": "/tmp/x"},
        user_id="user-1",
        tier="write",
        operation="file_write",
        ttl_seconds=300,
    )
    fetched = approval_store.get(approval.approval_id)
    assert fetched is not None
    assert fetched.approval_id == approval.approval_id


def test_approve_approval():
    approval = approval_store.create(
        tool_name="file_write",
        arguments={"file_path": "/tmp/x"},
        user_id="user-1",
        tier="write",
        operation="file_write",
        ttl_seconds=300,
    )
    resolved = approval_store.approve(approval.approval_id, resolved_by="admin-1")
    assert resolved is not None
    assert resolved.status == "approved"
    assert resolved.resolved_by == "admin-1"
    assert resolved.resolution == "approved"


def test_reject_approval():
    approval = approval_store.create(
        tool_name="file_write",
        arguments={"file_path": "/tmp/x"},
        user_id="user-1",
        tier="write",
        operation="file_write",
        ttl_seconds=300,
    )
    resolved = approval_store.reject(approval.approval_id, resolved_by="admin-1")
    assert resolved is not None
    assert resolved.status == "rejected"
    assert resolved.resolved_by == "admin-1"


def test_approval_expires():
    approval = approval_store.create(
        tool_name="file_write",
        arguments={"file_path": "/tmp/x"},
        user_id="user-1",
        tier="write",
        operation="file_write",
        ttl_seconds=0,
    )
    time.sleep(0.01)
    fetched = approval_store.get(approval.approval_id)
    assert fetched is None


def test_list_pending():
    a1 = approval_store.create("file_write", {"file_path": "/tmp/x"}, "user-1", "write", "file_write", ttl_seconds=300)
    a2 = approval_store.create("bash", {"command": "echo hi"}, "user-1", "dangerous", "bash", ttl_seconds=300)
    pending = approval_store.list_pending()
    assert len(pending) == 2
    assert {p.approval_id for p in pending} == {a1.approval_id, a2.approval_id}


def test_list_history():
    a1 = approval_store.create("file_write", {"file_path": "/tmp/x"}, "user-1", "write", "file_write", ttl_seconds=300)
    approval_store.approve(a1.approval_id, resolved_by="admin-1")
    history = approval_store.list_history()
    assert len(history) == 1
    assert history[0].approval_id == a1.approval_id


def test_get_stats():
    approval_store.create("file_write", {"file_path": "/tmp/x"}, "user-1", "write", "file_write", ttl_seconds=300)
    approval_store.create("bash", {"command": "rm -rf /"}, "user-1", "dangerous", "bash", ttl_seconds=300)
    stats = approval_store.get_stats()
    assert stats["pending"] == 2
    assert stats["approved"] == 0
    assert stats["rejected"] == 0


def test_cleanup_expired():
    approval_store.create("file_write", {"file_path": "/tmp/x"}, "user-1", "write", "file_write", ttl_seconds=0)
    approval_store.cleanup_expired()
    stats = approval_store.get_stats()
    assert stats["expired"] >= 1
