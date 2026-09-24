"""
Tests for product_polish.session_persistence

Uses only stdlib (tempfile) — no pytest plugins or external deps.
"""

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.session_persistence import SessionPersistence, SessionState  # noqa: E402


@pytest.fixture()
def persistence(tmp_path):
    sp = SessionPersistence(storage_dir=str(tmp_path))
    return sp


class TestSessionStateDataclass:
    def test_default_checksum_generated(self):
        ss = SessionState(session_id="s1", state={"a": 1})
        assert ss.checksum != ""

    def test_verify_checksum_true(self):
        ss = SessionState(session_id="s1", state={"a": 1})
        assert ss.verify_checksum() is True

    def test_checksum_changes_with_state(self):
        ss = SessionState(session_id="s1", state={"a": 1})
        c1 = ss.checksum
        ss.state["b"] = 2
        assert ss._compute_checksum() != c1

    def test_default_created_at_set(self):
        ss = SessionState(session_id="s1", state={})
        assert ss.created_at != ""

    def test_default_updated_at_set(self):
        ss = SessionState(session_id="s1", state={})
        assert ss.updated_at != ""

    def test_default_is_completed_false(self):
        ss = SessionState(session_id="s1", state={})
        assert ss.is_completed is False

    def test_post_init_generates_blank_checksum(self):
        ss = SessionState(session_id="s1", state={"x": 9}, checksum="")
        assert ss.checksum != ""

    def test_post_init_preserves_existing_checksum(self):
        ss = SessionState(session_id="s1", state={"a": 1}, checksum="abc123")
        assert ss.checksum == "abc123"

    def test_verify_checksum_false_after_state_change(self):
        ss = SessionState(session_id="s1", state={"a": 1})
        ss.state["b"] = 2
        assert ss.verify_checksum() is False

    def test_compute_checksum_deterministic(self):
        ss1 = SessionState(session_id="s1", state={"a": 1})
        ss2 = SessionState(session_id="s1", state={"a": 1})
        assert ss1.checksum == ss2.checksum


class TestSessionPersistenceInit:
    def test_storage_dir_set(self, tmp_path):
        sp = SessionPersistence(storage_dir=str(tmp_path))
        assert sp.storage_dir == str(tmp_path)

    def test_storage_dir_created(self, tmp_path):
        new_dir = tmp_path / "new" / "sessions"
        SessionPersistence(storage_dir=str(new_dir))
        assert new_dir.exists()

    def test_initial_stats_zero(self, tmp_path):
        sp = SessionPersistence(storage_dir=str(tmp_path))
        s = sp.get_stats()
        assert s["total_sessions"] == 0
        assert s["completed_sessions"] == 0
        assert s["active_sessions"] == 0


class TestSaveAndLoad:
    def test_save_creates_file(self, persistence, tmp_path):
        persistence.save_state("s1", {"v": 42})
        assert (tmp_path / "s1.json").exists()

    def test_save_returns_session_state(self, persistence):
        result = persistence.save_state("s1", {"v": 42})
        assert isinstance(result, SessionState)
        assert result.session_id == "s1"
        assert result.state == {"v": 42}

    def test_load_returns_none_missing(self, persistence):
        assert persistence.load_state("nonexistent") is None

    def test_load_returns_session_state(self, persistence):
        persistence.save_state("s1", {"a": 1})
        loaded = persistence.load_state("s1")
        assert loaded is not None
        assert loaded.session_id == "s1"
        assert loaded.state["a"] == 1

    def test_load_stores_in_internal_dict(self, persistence):
        persistence.save_state("s1", {"a": 1})
        persistence.load_state("s1")
        assert "s1" in persistence._states

    def test_save_overwrites_existing(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.save_state("s1", {"v": 2})
        loaded = persistence.load_state("s1")
        assert loaded.state["v"] == 2

    def test_save_creates_new_file(self, persistence, tmp_path):
        persistence.save_state("s2", {"v": 2})
        assert (tmp_path / "s2.json").exists()

    def test_load_corrupt_json_returns_none(self, persistence, tmp_path):
        (tmp_path / "bad.json").write_text("not-json-here")
        assert persistence.load_state("bad") is None

    def test_save_sets_checksum(self, persistence):
        result = persistence.save_state("s1", {"v": 42})
        assert result.checksum != ""

    def test_loaded_state_has_checksum(self, persistence):
        persistence.save_state("s1", {"v": 42})
        loaded = persistence.load_state("s1")
        assert loaded.checksum != ""


class TestResumeSession:
    def test_resume_returns_none_missing(self, persistence):
        assert persistence.resume_session("missing") is None

    def test_resume_returns_state_dict(self, persistence):
        persistence.save_state("s1", {"step": 1})
        assert persistence.resume_session("s1") == {"step": 1}

    def test_resume_returns_none_for_completed(self, persistence):
        persistence.save_state("s1", {"step": 1})
        persistence.complete_session("s1")
        assert persistence.resume_session("s1") is None

    def test_resume_returns_deep_copy(self, persistence):
        persistence.save_state("s1", {"step": 1})
        result = persistence.resume_session("s1")
        result["step"] = 999
        reloaded = persistence.resume_session("s1")
        assert reloaded["step"] == 1

    def test_resume_none_when_no_state_saved(self, persistence):
        assert persistence.resume_session("s1") is None


class TestCompleteSession:
    def test_complete_returns_true(self, persistence):
        persistence.save_state("s1", {"v": 1})
        assert persistence.complete_session("s1") is True

    def test_complete_returns_false_missing(self, persistence):
        assert persistence.complete_session("missing") is False

    def test_complete_markes_is_completed(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.complete_session("s1")
        loaded = persistence.load_state("s1")
        assert loaded.is_completed is True

    def test_complete_saves_final_state(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.complete_session("s1", final_state={"v": 99})
        loaded = persistence.load_state("s1")
        assert loaded.state["v"] == 99

    def test_complete_false_when_no_state_saved(self, persistence):
        assert persistence.complete_session("s1") is False

    def test_complete_twice(self, persistence):
        persistence.save_state("s1", {"v": 1})
        assert persistence.complete_session("s1") is True
        assert persistence.complete_session("s1") is True


class TestDeleteSession:
    def test_delete_returns_true(self, persistence):
        persistence.save_state("s1", {"v": 1})
        assert persistence.delete_session("s1") is True

    def test_delete_removes_file(self, persistence, tmp_path):
        persistence.save_state("s1", {"v": 1})
        persistence.delete_session("s1")
        assert not (tmp_path / "s1.json").exists()

    def test_delete_returns_true_for_missing(self, persistence):
        assert persistence.delete_session("missing") is True

    def test_delete_removes_from_internal_states(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.delete_session("s1")
        assert "s1" not in persistence._states

    def test_delete_cannot_resume_after(self, persistence):
        persistence.save_state("s1", {"step": 1})
        persistence.delete_session("s1")
        assert persistence.resume_session("s1") is None


class TestSessionHistory:
    def test_history_empty_when_no_saves(self, persistence):
        assert persistence.get_session_history("s1") == []

    def test_history_records_saves(self, persistence):
        persistence.save_state("s1", {"v": 1})
        history = persistence.get_session_history("s1")
        assert len(history) == 1

    def test_history_records_multiple_saves(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.save_state("s1", {"v": 2})
        history = persistence.get_session_history("s1")
        assert len(history) == 2

    def test_history_has_required_keys(self, persistence):
        persistence.save_state("s1", {"v": 1})
        entry = persistence.get_session_history("s1")[0]
        for key in ("created_at", "updated_at", "checksum", "is_completed"):
            assert key in entry

    def test_history_is_completed_false_by_default(self, persistence):
        persistence.save_state("s1", {"v": 1})
        entry = persistence.get_session_history("s1")[0]
        assert entry["is_completed"] is False


class TestListSessions:
    def test_list_empty_initially(self, persistence):
        assert persistence.list_sessions() == []

    def test_lists_persisted_session(self, persistence):
        persistence.save_state("s1", {"v": 1})
        assert "s1.json" in persistence.list_sessions()

    def test_lists_multiple(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.save_state("s2", {"v": 2})
        assert sorted(persistence.list_sessions()) == ["s1.json", "s2.json"]

    def test_list_sorted(self, persistence):
        persistence.save_state("zzz", {"v": 1})
        persistence.save_state("aaa", {"v": 1})
        sessions = persistence.list_sessions()
        assert sessions == ["aaa.json", "zzz.json"]

    def test_list_excludes_non_json(self, persistence, tmp_path):
        (tmp_path / "readme.txt").write_text("hi")
        persistence.save_state("s1", {"v": 1})
        sessions = persistence.list_sessions()
        assert all(s.endswith(".json") for s in sessions)
        assert "readme.txt" not in sessions


class TestGetStats:
    def test_stats_zero_initially(self, persistence):
        s = persistence.get_stats()
        assert s["total_sessions"] == 0

    def test_stats_after_save(self, persistence):
        persistence.save_state("s1", {"v": 1})
        s = persistence.get_stats()
        assert s["total_sessions"] == 1
        assert s["active_sessions"] == 1

    def test_stats_after_complete(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.complete_session("s1")
        s = persistence.get_stats()
        assert s["completed_sessions"] == 1
        assert s["active_sessions"] == 0

    def test_stats_completes_reduces_active(self, persistence):
        persistence.save_state("s1", {"v": 1})
        persistence.save_state("s2", {"v": 1})
        persistence.complete_session("s1")
        s = persistence.get_stats()
        assert s["total_sessions"] == 2
        assert s["active_sessions"] == 1
        assert s["completed_sessions"] == 1


class TestChecksumValidation:
    def test_load_validates_checksum(self, persistence, tmp_path):
        persistence.save_state("s1", {"a": 1})
        loaded = persistence.load_state("s1")
        assert loaded.verify_checksum() is True

    def test_checksum_changes_on_new_state(self, persistence):
        ss1 = SessionState(session_id="s1", state={"a": 1})
        ss2 = SessionState(session_id="s1", state={"b": 2})
        assert ss1.checksum != ss2.checksum


class TestDiskIO:
    def test_load_after_save_same_dir(self, persistence, tmp_path):
        persistence.save_state("s1", {"v": 42})
        sp2 = SessionPersistence(storage_dir=str(tmp_path))
        loaded = sp2.load_state("s1")
        assert loaded is not None
        assert loaded.state["v"] == 42

    def test_save_writes_valid_json(self, persistence, tmp_path):
        persistence.save_state("s1", {"v": 1})
        raw = (tmp_path / "s1.json").read_text()
        import json
        data = json.loads(raw)
        assert data["session_id"] == "s1"

    def test_load_recreates_session_state(self, persistence):
        persistence.save_state("s1", {"v": 1})
        loaded = persistence.load_state("s1")
        assert isinstance(loaded, SessionState)
