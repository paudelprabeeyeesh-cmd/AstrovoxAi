"""Single, safe environment loader.

``python-dotenv`` parses the file on every call and a malformed ``.env``
costs a warning plus a retry each time. The previous code called
``load_dotenv()`` four times during import, so one junk ``.env`` cost four
parse cycles and — more importantly — each failure was silent and
non-fatal, which hid a broken production environment.

This helper:

* loads once, from the project root, at first use;
* treats a missing or malformed file as a warning, never an exception,
  because the process env is still usable;
* returns what happened so a startup check can be explicit about it.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_loaded = False
_status: dict = {"loaded": False, "path": None, "error": None, "reason": None}


def _candidate_paths() -> list[Path]:
    """Search upward from this file and the CWD for a .env."""
    here = Path(__file__).resolve()
    roots: list[Path] = []

    # 02-Backend/app/env_loader.py -> repo root is three levels up.
    roots.append(here.parents[2])

    cwd = Path(os.getcwd())
    roots.append(cwd)
    roots.append(cwd.parent)

    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        try:
            root = root.resolve()
        except OSError:  # pragma: no cover - defensive
            continue
        if root in seen:
            continue
        seen.add(root)
        out.append(root / ".env")
    return out


def load_environment(force: bool = False) -> dict:
    """Load .env once. Returns a status dict; never raises."""
    global _loaded
    if _loaded and not force:
        return dict(_status)

    from dotenv import load_dotenv

    path: Optional[Path] = None
    for candidate in _candidate_paths():
        if candidate.is_file():
            path = candidate
            break

    if path is None:
        _status.update(
            loaded=False, path=None, error=None,
            reason="no .env file found; using the process environment",
        )
        logger.debug("env_loader: no .env file found")
    else:
        parsed = load_dotenv(dotenv_path=str(path), override=False, verbose=False)
        _status.update(
            loaded=bool(parsed), path=str(path), error=None,
            reason="loaded" if parsed else "file present but no keys were set",
        )
        if not parsed:
            logger.warning(
                "env_loader: %s could not be parsed or contains no keys; "
                "using the process environment",
                path,
            )

    _loaded = True
    return dict(_status)


def env_status() -> dict:
    """Return the load status without triggering a load."""
    return dict(_status)


def env_path() -> Optional[str]:
    return _status.get("path")


def has_env_file() -> bool:
    return _status.get("path") is not None
