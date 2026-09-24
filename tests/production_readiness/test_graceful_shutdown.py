"""Tests for production_readiness graceful_shutdown."""
from __future__ import annotations

from unittest.mock import MagicMock

from production_readiness.graceful_shutdown import GracefulShutdown


def test_initial_state() -> None:
    gs = GracefulShutdown()
    assert gs.is_up() is True
    assert gs.is_shutting_down() is False


def test_shutdown_changes_state() -> None:
    gs = GracefulShutdown()
    gs.shutdown()
    assert gs.is_up() is False
    assert gs.is_shutting_down() is True


def test_stop_triggers_exit() -> None:
    gs = GracefulShutdown()
    on_exit = MagicMock()
    gs.register_exit(on_exit)
    gs.stop()
    assert gs.is_up() is False
    on_exit.assert_called_once()
