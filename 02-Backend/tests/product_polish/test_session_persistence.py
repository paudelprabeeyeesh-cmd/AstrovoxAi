import json
import os
from product_polish.session_persistence import SessionPersistence, SessionState


def test_session_state_auto_timestamps_and_checksum(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    state = sp.save_state("s1", {"key": "value"})
    assert state.created_at != ""
    assert state.updated_at != ""
    assert state.checksum != ""


def test_session_state_verify_checksum_pass():
    state = SessionState(session_id="s1", state={"a": 1})
    assert state.verify_checksum() is True


def test_session_state_verify_checksum_fail():
    state = SessionState(session_id="s1", state={"a": 1}, checksum="bad")
    assert state.verify_checksum() is False


def test_save_and_load_state(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {"step": 1})
    loaded = sp.load_state("s1")
    assert loaded is not None
    assert loaded.state["step"] == 1


def test_load_missing_returns_none(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    assert sp.load_state("missing") is None


def test_resume_session(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {"step": 1})
    assert sp.resume_session("s1") == {"step": 1}


def test_resume_completed_session_returns_none(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {"step": 1})
    sp.complete_session("s1")
    assert sp.resume_session("s1") is None


def test_complete_session(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {"step": 1})
    result = sp.complete_session("s1", final_state={"step": 2})
    assert result is True
    loaded = sp.load_state("s1")
    assert loaded.is_completed is True
    assert loaded.state["step"] == 2


def test_complete_missing_session_returns_false(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    assert sp.complete_session("missing") is False


def test_delete_session(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {"step": 1})
    assert sp.delete_session("s1") is True
    assert sp.load_state("s1") is None
    assert sp.list_sessions() == []


def test_get_session_history(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {"step": 1})
    sp.save_state("s1", {"step": 2})
    history = sp.get_session_history("s1")
    assert len(history) == 2


def test_list_sessions(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {})
    sp.save_state("s2", {})
    sessions = sp.list_sessions()
    assert sessions == ["s1.json", "s2.json"]


def test_get_stats(tmp_path):
    sp = SessionPersistence(str(tmp_path))
    sp.save_state("s1", {})
    sp.save_state("s2", {})
    sp.complete_session("s1")
    stats = sp.get_stats()
    assert stats["total_sessions"] == 2
    assert stats["completed_sessions"] == 1
    assert stats["active_sessions"] == 1
