"""Tests for production_readiness startup_sequence."""
from __future__ import annotations

from production_readiness.startup_sequence import StartupSequence


def test_run_success() -> None:
    ss = StartupSequence()
    ss.add_step("migrations", lambda: {"ok": True})
    ss.add_step("cache_warmup", lambda: {"ok": True})
    success, completed, failed = ss.run()
    assert success is True
    assert completed == ["migrations", "cache_warmup"]
    assert failed == []


def test_run_with_failure() -> None:
    ss = StartupSequence()
    ss.add_step("migrations", lambda: {"ok": True})

    def bad() -> Dict[str, Any]:
        raise RuntimeError("fail")

    ss.add_step("cache_warmup", bad)
    success, completed, failed = ss.run()
    assert success is False
    assert completed == ["migrations"]
    assert failed == ["cache_warmup"]
