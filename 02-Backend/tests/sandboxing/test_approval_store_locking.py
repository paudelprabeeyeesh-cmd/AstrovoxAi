"""Regression tests for approval-store locking.

`cleanup_expired` used to call `_archive` while still holding the store's
non-reentrant lock, so `_archive` blocked forever trying to re-acquire it.
The suite hung rather than failed, which is why these tests assert that the
call RETURNS rather than that it produced a value.
"""

import threading
import time

from sandboxing.approval_store import ApprovalStore


def test_cleanup_expired_returns():
    """cleanup_expired must terminate, not deadlock on its own lock."""
    store = ApprovalStore()
    store.create("write_file", {"path": "/tmp/x"}, "u1", "elevated", "write", ttl_seconds=0)

    done = threading.Event()

    def run():
        store.cleanup_expired()
        done.set()

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    assert done.wait(timeout=5), "cleanup_expired deadlocked"
    worker.join(timeout=5)


def test_cleanup_archives_expired_to_history():
    """Expired approvals are still recorded in history after the fix."""
    store = ApprovalStore()
    approval = store.create(
        "run_command", {"cmd": "ls"}, "u1", "elevated", "execute", ttl_seconds=0
    )
    store.cleanup_expired()

    assert approval.status == "expired"
    assert any(a.approval_id == approval.approval_id for a in store.list_history())


def test_approve_does_not_deadlock():
    """Approve and reject archive without holding the lock."""
    store = ApprovalStore()
    approval = store.create("http_request", {"url": "https://x"}, "u1", "elevated", "network")

    done = threading.Event()

    def run():
        store.approve(approval.approval_id, resolved_by="admin")
        done.set()

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    assert done.wait(timeout=5), "approve deadlocked"
    assert store.get_stats()["approved"] == 1


def test_repeated_cleanup_is_idempotent():
    """A second sweep over the same expired entry is a no-op."""
    store = ApprovalStore()
    approval = store.create(
        "run_command", {"cmd": "ls"}, "u1", "elevated", "execute", ttl_seconds=0
    )
    store.cleanup_expired()
    first = len(store.list_history())
    store.cleanup_expired()
    assert len(store.list_history()) == first
