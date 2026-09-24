import time
import pytest
from production_readiness.session_management import SessionStore, SessionManager


def test_session_create():
    manager = SessionManager()
    session = manager.create_session("user-1")
    assert session.user_id == "user-1"
    assert session.session_id is not None


def test_session_get():
    manager = SessionManager()
    session = manager.create_session("user-1")
    fetched = manager.get_session(session.session_id)
    assert fetched is not None
    assert fetched.user_id == "user-1"


def test_session_by_user():
    manager = SessionManager()
    session = manager.create_session("user-1")
    fetched = manager.get_session_by_user("user-1")
    assert fetched is not None
    assert fetched.session_id == session.session_id


def test_session_destroy():
    manager = SessionManager()
    session = manager.create_session("user-1")
    manager.destroy_session(session.session_id)
    assert manager.get_session(session.session_id) is None


def test_session_cleanup():
    manager = SessionManager()
    session = manager.create_session("user-1")
    removed = manager.cleanup(0.1)
    assert removed == 0


def test_session_count():
    manager = SessionManager()
    manager.create_session("user-1")
    manager.create_session("user-2")
    assert manager.count() == 2


def test_session_sticky():
    manager = SessionManager()
    session = manager.create_session("user-1", sticky=True)
    sticky = manager.sticky_sessions()
    assert sticky[0].sticky is True


def test_session_store_cleanup():
    store = SessionStore()
    store.create("user-1", "backend-1")
    store.cleanup(0.0)
    assert store.count() == 0
