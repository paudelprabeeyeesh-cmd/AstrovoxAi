from __future__ import annotations

import pytest

from memory_persistence.session_persistence import SessionPersistence


@pytest.fixture
def persistence(tmp_path):
    return SessionPersistence(storage_dir=str(tmp_path))


def test_save_and_load_state(persistence):
    state = persistence.save_state("s1", {"key": "value"})
    assert state.session_id == "s1"
    loaded = persistence.load_state("s1")
    assert loaded is not None
    assert loaded.state["key"] == "value"


def test_verify_checksum(persistence):
    state = persistence.save_state("s1", {"key": "value"})
    assert state.verify_checksum() is True


def test_resume_session(persistence):
    persistence.save_state("s1", {"step": 1})
    resumed = persistence.resume_session("s1")
    assert resumed == {"step": 1}


def test_resume_completed_session(persistence):
    persistence.save_state("s1", {"step": 1})
    persistence.complete_session("s1")
    assert persistence.resume_session("s1") is None


def test_complete_session(persistence):
    persistence.save_state("s1", {"step": 1})
    assert persistence.complete_session("s1") is True
    loaded = persistence.load_state("s1")
    assert loaded.is_completed is True


def test_delete_session(persistence):
    persistence.save_state("s1", {"step": 1})
    assert persistence.delete_session("s1") is True
    assert persistence.load_state("s1") is None


def test_list_sessions(persistence):
    persistence.save_state("s1", {})
    persistence.save_state("s2", {})
    sessions = persistence.list_sessions()
    assert set(sessions) == {"s1", "s2"}


def test_get_session_history(persistence):
    persistence.save_state("s1", {"step": 1})
    persistence.save_state("s1", {"step": 2})
    history = persistence.get_session_history("s1")
    assert len(history) == 2
    assert history[0]["checksum"] != ""


def test_get_stats(persistence):
    persistence.save_state("s1", {})
    stats = persistence.get_stats()
    assert stats["total_sessions"] == 1
    assert stats["active_sessions"] == 1
    assert stats["completed_sessions"] == 0
