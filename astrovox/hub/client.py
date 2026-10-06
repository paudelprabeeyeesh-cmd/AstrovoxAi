"""Uploading and downloading from the Hugging Face Hub.

Built on the official ``huggingface_hub`` package rather than hand-rolled HTTP,
so authentication, retries, and resumable transfers come from the client that
maintains them. That dependency is imported lazily: the rest of Astrovox works
without it, and only these operations need it.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from astrovox.hub import auth as hub_auth
from astrovox.hub.card import ModelInfo, build_card, build_manifest
from astrovox.hub.checkpoint import (
    ModelBundle,
    collect_bundle,
)

#: Name given to the weight file in the repository, whatever it was called
#: locally, so that a downstream loader can find it at a predictable path.
REMOTE_WEIGHTS_NAME = "model.avz"

#: Name of the machine-readable manifest beside the weights.
REMOTE_MANIFEST_NAME = "astrovox_manifest.json"


class HubError(RuntimeError):
    """Raised when a Hub operation fails."""


class RepositoryNotFound(HubError):
    """Raised when a repository does not exist."""


class _MissingDependency(HubError):
    """Raised when ``huggingface_hub`` is not installed."""


def _require_library() -> Any:
    """Import and return ``huggingface_hub``, with a usable error if absent."""
    try:
        import huggingface_hub
    except ImportError as exc:
        raise _MissingDependency(
            "The Hugging Face Hub integration needs the 'huggingface_hub' package. "
            "Install it with: pip install huggingface_hub"
        ) from exc
    return huggingface_hub


def parse_repo_id(repo_id: str) -> tuple[str | None, str]:
    """Split ``namespace/name`` or ``name`` into its parts.

    A bare name has no namespace, which is legal: the Hub resolves it to the
    authenticated account.
    """
    cleaned = repo_id.strip().strip("/")
    if not cleaned:
        raise HubError("Repository id cannot be empty")
    if "/" in cleaned:
        namespace, _, name = cleaned.partition("/")
        if not namespace or not name or "/" in name:
            raise HubError(f"Malformed repository id: {repo_id!r}")
        return namespace, name
    return None, cleaned


def normalize_repo_id(repo_id: str) -> str:
    """Return the repository id with a namespace, using the caller if absent."""
    namespace, name = parse_repo_id(repo_id)
    return f"{namespace}/{name}" if namespace else name


@dataclass
class PushResult:
    """What a successful upload did."""

    repo_id: str
    created: bool
    uploaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    commit_url: str = ""

    @property
    def url(self) -> str:
        """The repository page on the Hub."""
        return f"https://huggingface.co/{self.repo_id}"

    def to_dict(self) -> dict[str, Any]:
        """Return the result as a plain dictionary."""
        return {
            "repo_id": self.repo_id,
            "created": self.created,
            "uploaded": self.uploaded,
            "skipped": self.skipped,
            "commit_url": self.commit_url,
            "url": self.url,
        }


@dataclass
class PullResult:
    """What a successful download produced."""

    repo_id: str
    directory: Path
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the result as a plain dictionary."""
        return {
            "repo_id": self.repo_id,
            "directory": str(self.directory),
            "files": self.files,
        }


def stage_bundle(
    bundle: ModelBundle,
    repo_id: str,
    output: str | Path | None = None,
    info: ModelInfo | None = None,
    include_readme: bool = True,
) -> Path:
    """Assemble the exact file set a push will send into a directory.

    Staging separately from uploading means the file list is inspectable and
    testable without a network, and the same set is used for both.

    Args:
        bundle: the discovered checkpoint and its companions.
        repo_id: the repository being pushed to.
        output: staging directory; a temporary one is used when omitted.
        info: overrides for the generated card.
        include_readme: whether to write a model card.

    Returns:
        The directory holding the staged files.
    """
    if output is None:
        staging = Path(tempfile.mkdtemp(prefix="astrovox_push_"))
    else:
        staging = Path(output).expanduser()
        staging.mkdir(parents=True, exist_ok=True)

    shutil.copy2(bundle.checkpoint.path, staging / REMOTE_WEIGHTS_NAME)

    for path in bundle.tokenizer_files + bundle.companion_files:
        if path.is_file():
            # Config is renamed so a downstream loader knows where to look.
            target = "astrovox_config.json" if path.name == "config.json" else path.name
            shutil.copy2(path, staging / target)

    card_info = info or ModelInfo.from_bundle(normalize_repo_id(repo_id), bundle)
    manifest = build_manifest(card_info, filename=REMOTE_WEIGHTS_NAME)
    (staging / REMOTE_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    if include_readme:
        (staging / "README.md").write_text(
            build_card(card_info, filename=REMOTE_WEIGHTS_NAME), encoding="utf-8"
        )
    return staging


def push_model(
    repo_id: str,
    root: str | Path = ".",
    checkpoint: str | Path | None = None,
    token: str | None = None,
    private: bool = False,
    exist_ok: bool = True,
    commit_message: str | None = None,
    staging: str | Path | None = None,
    include_readme: bool = True,
    info: ModelInfo | None = None,
    progress: Callable[[str], None] | None = None,
) -> PushResult:
    """Upload a trained model to the Hub, creating the repository if needed.

    Args:
        repo_id: ``namespace/name``; a bare name uses the token's account.
        root: directory to search for a checkpoint.
        checkpoint: explicit checkpoint path, skipping the search.
        token: access token; read from the environment or stored credentials
            when omitted.
        private: create the repository as private.
        exist_ok: update an existing repository rather than failing.
        commit_message: message for the upload commit.
        staging: directory to assemble files in; a temporary one by default.
        include_readme: whether to generate a model card.
        info: overrides for the generated card.
        progress: called with human-readable progress messages.

    Raises:
        CheckpointNotFound: when no checkpoint can be located.
        HubError: when the upload fails.
    """
    hub = _require_library()
    resolved_id = normalize_repo_id(repo_id)
    emit = progress or (lambda message: None)

    # The checkpoint is found before the token is required: it is a local,
    # fast check, and a user pointing at the wrong directory should hear
    # about that rather than about authentication.
    emit(f"Looking for a checkpoint under {Path(root).expanduser().resolve()}")
    bundle = collect_bundle(root, checkpoint)
    emit(
        f"Found {bundle.checkpoint.name} "
        f"({bundle.checkpoint.size_mb:.1f} MB)"
    )

    resolved_token = token or hub_auth.require_token()

    directory = stage_bundle(bundle, resolved_id, staging, info, include_readme)
    files = sorted(p for p in directory.iterdir() if p.is_file())
    emit(f"Staged {len(files)} file(s) in {directory}")

    created = False
    try:
        hub.create_repo(
            repo_id=resolved_id,
            token=resolved_token,
            private=private,
            exist_ok=exist_ok,
            repo_type="model",
        )
        created = True
        emit(f"Repository {resolved_id} is ready")
    except Exception as exc:
        # create_repo with exist_ok=True should not raise for an existing repo,
        # but an older client version may. Only a real failure is worth raising.
        if not _looks_like_exists(exc):
            raise HubError(f"Could not prepare repository {resolved_id}: {exc}") from exc
        emit(f"Repository {resolved_id} already exists")

    api = hub.HfApi(token=resolved_token)
    try:
        api.upload_folder(
            folder_path=str(directory),
            repo_id=resolved_id,
            commit_message=commit_message or "Upload model with astrovox push",
            ignore_patterns=["*.tmp", ".DS_Store"],
        )
    except Exception as exc:
        raise HubError(f"Upload to {resolved_id} failed: {exc}") from exc

    emit(f"Uploaded {len(files)} file(s) to https://huggingface.co/{resolved_id}")
    return PushResult(
        repo_id=resolved_id,
        created=created,
        uploaded=[p.name for p in files],
        commit_url=f"https://huggingface.co/{resolved_id}",
    )


def _looks_like_exists(exc: Exception) -> bool:
    """Return whether an exception means the repository already exists."""
    text = str(exc).lower()
    return "already exist" in text or "409" in text


def pull_model(
    repo_id: str,
    directory: str | Path | None = None,
    token: str | None = None,
    revision: str | None = None,
    allow_patterns: Sequence[str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> PullResult:
    """Download a model repository from the Hub.

    Args:
        repo_id: the repository to fetch.
        directory: where to put it; a temporary directory when omitted.
        token: access token, needed for private repositories.
        revision: branch, tag, or commit to fetch.
        allow_patterns: filename globs to restrict the download to.
        progress: called with human-readable progress messages.

    Raises:
        HubError: when the download fails.
    """
    hub = _require_library()
    emit = progress or (lambda message: None)
    resolved_token = token or hub_auth.read_token()
    resolved_id = normalize_repo_id(repo_id)
    target = (
        Path(directory).expanduser()
        if directory
        else Path(tempfile.mkdtemp(prefix="astrovox_pull_"))
    )
    target.mkdir(parents=True, exist_ok=True)

    emit(f"Downloading {resolved_id} to {target}")
    try:
        from huggingface_hub import snapshot_download

        path = snapshot_download(
            repo_id=resolved_id,
            token=resolved_token,
            revision=revision,
            local_dir=str(target),
            allow_patterns=list(allow_patterns) if allow_patterns else None,
        )
    except Exception as exc:
        if "404" in str(exc) or "not found" in str(exc).lower():
            raise RepositoryNotFound(f"Repository {resolved_id} does not exist") from exc
        raise HubError(f"Download from {resolved_id} failed: {exc}") from exc

    files = sorted(p.name for p in Path(path).iterdir() if p.is_file())
    emit(f"Downloaded {len(files)} file(s)")
    return PullResult(repo_id=resolved_id, directory=target, files=files)


def list_models(
    author: str | None = None,
    search: str | None = None,
    limit: int = 50,
    token: str | None = None,
    sort: str = "lastModified",
    direction: int = -1,
) -> list[dict[str, Any]]:
    """List models, optionally filtered by author or a search term.

    Returns:
        One dictionary per model with its id, author, downloads, likes, and
        modification time.

    Raises:
        HubError: when the listing fails.
    """
    hub = _require_library()
    api = hub.HfApi(token=token)
    try:
        found = api.list_models(
            author=author,
            search=search,
            limit=limit,
            sort=sort,
            direction=direction,
            full=False,
        )
    except Exception as exc:
        raise HubError(f"Could not list models: {exc}") from exc

    results = []
    for model in found:
        results.append(
            {
                "id": getattr(model, "id", ""),
                "author": getattr(model, "author", ""),
                "downloads": getattr(model, "downloads", 0),
                "likes": getattr(model, "likes", 0),
                "last_modified": str(getattr(model, "lastModified", "")),
                "tags": list(getattr(model, "tags", []) or [])[:8],
            }
        )
    return results


def repo_info(repo_id: str, token: str | None = None) -> dict[str, Any]:
    """Return metadata about one repository."""
    hub = _require_library()
    api = hub.HfApi(token=token or hub_auth.read_token())
    try:
        info = api.model_info(normalize_repo_id(repo_id))
    except Exception as exc:
        if "404" in str(exc) or "not found" in str(exc).lower():
            raise RepositoryNotFound(f"Repository {repo_id} does not exist") from exc
        raise HubError(f"Could not read metadata for {repo_id}: {exc}") from exc
    return {
        "id": getattr(info, "id", repo_id),
        "sha": getattr(info, "sha", ""),
        "private": getattr(info, "private", False),
        "downloads": getattr(info, "downloads", 0),
        "likes": getattr(info, "likes", 0),
        "tags": list(getattr(info, "tags", []) or []),
        "last_modified": str(getattr(info, "lastModified", "")),
    }


def model_card(model_id: str, token: str | None = None) -> str:
    """Download and return a repository's model card."""
    hub = _require_library()
    resolved_token = token or hub_auth.read_token()
    try:
        path = hub.hf_hub_download(
            repo_id=normalize_repo_id(model_id),
            filename="README.md",
            token=resolved_token,
        )
    except Exception as exc:
        raise HubError(f"Could not read the model card for {model_id}: {exc}") from exc
    return Path(path).read_text(encoding="utf-8")


def describe_local_model(root: str | Path = ".", repo_id: str = "local/model") -> ModelInfo:
    """Build a :class:`ModelInfo` for a local checkpoint without pushing it.

    Useful for previewing the card that a push would produce.
    """
    bundle = collect_bundle(root)
    return ModelInfo.from_bundle(normalize_repo_id(repo_id), bundle)