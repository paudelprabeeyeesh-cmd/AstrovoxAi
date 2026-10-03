"""Authentication and credential storage for the Hugging Face Hub.

A token is read from, in order: an explicit argument, the ``HF_TOKEN``
environment variable, a file under the user's config directory, or the cache
that the ``huggingface_hub`` package itself maintains. Tokens are never logged
and never written to a repository.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Where the token is stored when the environment does not provide one.
DEFAULT_CREDENTIAL_PATH = Path.home() / ".astrovox" / "token"


class AuthenticationError(RuntimeError):
    """Raised when no usable token can be found."""


def credential_path(path: str | Path | None = None) -> Path:
    """Return the file the token is read from and written to."""
    if path is not None:
        return Path(path).expanduser()
    override = os.environ.get("ASTROVOX_TOKEN_FILE")
    if override:
        return Path(override).expanduser()
    return DEFAULT_CREDENTIAL_PATH


def _mask(token: str) -> str:
    """Return a token with all but its last four characters hidden."""
    if len(token) <= 4:
        return "*" * len(token)
    return f"{'*' * (len(token) - 4)}{token[-4:]}"


def read_token(path: str | Path | None = None) -> str | None:
    """Return the stored token, or ``None`` when there is none.

    The environment wins over the file so that a token can be supplied per
    command in CI without editing anything on disk.
    """
    for candidate in (os.environ.get("ASTROVOX_TOKEN"), os.environ.get("HF_TOKEN")):
        if candidate and candidate.strip():
            return candidate.strip()

    target = credential_path(path)
    if target.is_file():
        contents = target.read_text(encoding="utf-8").strip()
        return contents or None
    return None


def write_token(token: str, path: str | Path | None = None) -> Path:
    """Store ``token`` and return the file it was written to.

    The file is owner-readable only, since a token grants write access to
    whatever repositories it can reach.
    """
    if not token or not token.strip():
        raise AuthenticationError("Refusing to store an empty token")
    target = credential_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token.strip(), encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        # Some filesystems do not support permissions; the token is still stored.
        pass
    return target


def delete_token(path: str | Path | None = None) -> bool:
    """Remove the stored token; returns whether one was there."""
    target = credential_path(path)
    if target.is_file():
        target.unlink()
        return True
    return False


def require_token(path: str | Path | None = None) -> str:
    """Return the token or explain how to supply one."""
    token = read_token(path)
    if not token:
        raise AuthenticationError(
            "No Hugging Face token found. Run 'astrovox login', or set HF_TOKEN "
            "in the environment."
        )
    return token


@dataclass
class Identity:
    """The account a token belongs to."""

    username: str
    token: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the identity, with the token masked."""
        return {"username": self.username, "token": _mask(self.token) if self.token else None}


def whoami(token: str | None = None, path: str | Path | None = None) -> Identity:
    """Return the account the current token belongs to."""
    from astrovox.hub.client import _require_library

    hub = _require_library()
    resolved = token or require_token(path)
    try:
        info = hub.whoami(token=resolved)
    except Exception as exc:  # pragma: no cover - depends on network state
        raise AuthenticationError(f"Could not verify the token: {exc}") from exc
    return Identity(username=info.get("name", "unknown"), token=resolved)


def login(token: str, path: str | Path | None = None, verify: bool = True) -> Identity:
    """Verify ``token`` if possible, store it, and return the identity.

    Verification is attempted but a failure is reported rather than raised, so
    a token can still be stored for a repository the account cannot see yet.
    """
    target = write_token(token, path)
    if not verify:
        return Identity(username="unverified", token=token)
    try:
        identity = whoami(token=token, path=path)
    except AuthenticationError as exc:
        return Identity(username=f"stored, unverified ({exc})", token=token)
    return identity


def logout(path: str | Path | None = None) -> bool:
    """Remove the stored token."""
    return delete_token(path)


def status(path: str | Path | None = None) -> dict[str, Any]:
    """Describe the current authentication state without revealing the token."""
    token = read_token(path)
    return {
        "authenticated": token is not None,
        "source": (
            "environment"
            if os.environ.get("ASTROVOX_TOKEN") or os.environ.get("HF_TOKEN")
            else "file"
            if token
            else None
        ),
        "path": str(credential_path(path)),
        "masked": _mask(token) if token else None,
    }