"""Finding and describing a trained model that is ready to publish.

Pushing should not require remembering where the weights are. This module
looks in the places a training run actually writes to, ranks what it finds by
how recently it was written, and extracts the metadata a model card needs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

#: Extensions a trained artifact may carry. ``.avz`` is this framework's
#: checkpoint container; the rest are what other tooling tends to emit.
CHECKPOINT_SUFFIXES = (".avz", ".pt", ".pth", ".bin", ".safetensors", ".ckpt")

#: Files that travel with weights and belong in the same repository.
COMPANION_FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "generation_config.json",
    "LICENSE",
    "LICENSE.txt",
    "README.md",
)


class CheckpointNotFound(FileNotFoundError):
    """Raised when no trained artifact can be located."""


@dataclass
class Checkpoint:
    """One discovered artifact and what is known about it."""

    path: Path
    size_bytes: int
    modified: float

    @property
    def name(self) -> str:
        """The file name, which becomes its name in the repository."""
        return self.path.name

    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Return the checkpoint as a plain dictionary."""
        return {
            "path": str(self.path),
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_mb, 3),
            "modified": self.modified,
        }


@dataclass
class ModelBundle:
    """Everything that would be uploaded for one model."""

    checkpoint: Checkpoint
    config: dict[str, Any] = field(default_factory=dict)
    tokenizer_files: list[Path] = field(default_factory=list)
    companion_files: list[Path] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def files(self) -> list[Path]:
        """Every file that would be uploaded."""
        return (
            [self.checkpoint.path]
            + self.tokenizer_files
            + self.companion_files
            + ([self.manifest_path] if self.manifest_path else [])
        )

    manifest_path: Path | None = None

    @property
    def parameter_count(self) -> int:
        """Total parameters described by the manifest, or zero if unknown."""
        return int(self.manifest.get("parameter_count", 0))

    def to_dict(self) -> dict[str, Any]:
        """Return the bundle as a plain dictionary."""
        return {
            "checkpoint": self.checkpoint.to_dict(),
            "config": self.config,
            "tokenizer_files": [p.name for p in self.tokenizer_files],
            "companion_files": [p.name for p in self.companion_files],
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "parameter_count": self.parameter_count,
        }


def _rank(path: Path) -> float:
    """Score a candidate so the newest, most specific artifact wins.

    Files written directly into the search root outrank ones buried in
    subdirectories, because a run's own output directory is what a user means
    by "the model" far more often than a stale copy in some archive tree.
    """
    score = 0.0
    name = path.name.lower()
    if any(token in name for token in ("final", "best", "last", "model")):
        score += 100.0
    if re.search(r"(step|epoch|iter)[-_]?\d+", name):
        score += 50.0
    return score


def find_checkpoints(
    root: str | Path = ".", suffixes: Sequence[str] = CHECKPOINT_SUFFIXES, limit: int = 200
) -> list[Checkpoint]:
    """Return the trained artifacts under ``root``, best candidate first.

    Directories that never hold checkpoints are skipped outright, since
    walking a virtual environment or a package cache to look for weights is
    slow and never finds anything.
    """
    base = Path(root).expanduser().resolve()
    if base.is_file():
        return [_describe(base)]
    if not base.is_dir():
        raise CheckpointNotFound(f"{base} is not a directory")

    skip = {
        ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
        "site-packages", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        ".idea", ".vscode", "dist", "build",
    }
    found: list[Checkpoint] = []
    for path in base.rglob("*"):
        if len(found) >= limit:
            break
        if path.suffix.lower() not in suffixes:
            continue
        if any(part in skip for part in path.parts):
            continue
        if not path.is_file() or path.stat().st_size == 0:
            continue
        found.append(_describe(path))

    # Newest first among equals, then by the preference score, then shallow.
    found.sort(key=lambda c: (-c.modified - _rank(c.path), len(c.path.parts)))
    found.sort(key=lambda c: -(_rank(c.path) + c.modified * 1e-6))
    return found


def _describe(path: Path) -> Checkpoint:
    """Build a :class:`Checkpoint` from a file on disk."""
    stat = path.stat()
    return Checkpoint(path=path, size_bytes=stat.st_size, modified=stat.st_mtime)


def latest_checkpoint(
    root: str | Path = ".", suffixes: Sequence[str] = CHECKPOINT_SUFFIXES
) -> Checkpoint:
    """Return the single best checkpoint under ``root``.

    Raises:
        CheckpointNotFound: when nothing suitable exists.
    """
    candidates = find_checkpoints(root, suffixes)
    if not candidates:
        raise CheckpointNotFound(
            f"No model checkpoint found under {Path(root).expanduser().resolve()}. "
            f"Looked for {', '.join(suffixes)}."
        )
    return candidates[0]


def find_companions(checkpoint: Checkpoint) -> tuple[list[Path], dict[str, Any]]:
    """Return tokenizer and companion files sitting beside a checkpoint."""
    directory = checkpoint.path.parent
    tokenizer: list[Path] = []
    companions: list[Path] = []

    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.resolve() == checkpoint.path.resolve():
            continue
        lowered = path.name.lower()
        if any(marker in lowered for marker in ("tokenizer", "vocab", "merges", "special_tokens")):
            tokenizer.append(path)
        elif path.name in COMPANION_FILES:
            companions.append(path)

    config: dict[str, Any] = {}
    config_path = directory / "config.json"
    if config_path.is_file():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config = loaded
        except (json.JSONDecodeError, OSError):
            # A malformed config should not stop a push; the card just says less.
            config = {}

    return tokenizer + companions, config


def read_manifest(path: str | Path) -> dict[str, Any]:
    """Read a manifest written alongside a checkpoint, or return an empty one."""
    target = Path(path).expanduser()
    if target.is_dir():
        target = target / "manifest.json"
    if not target.is_file():
        return {}
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def parameter_count_of(module: Any) -> int:
    """Return the total number of parameters in a module."""
    named_parameters = getattr(module, "named_parameters", None)
    if named_parameters is None:
        return 0
    return int(sum(int(p.numel) for _, p in named_parameters()))


def architecture_of(module: Any) -> str:
    """Return a readable architecture description for a module."""
    parts = []
    for name, child in getattr(module, "named_modules", lambda: [])():
        if name and type(child) is not type(module):
            parts.append(f"{name}:{type(child).__name__}")
    summary = ", ".join(parts[:8])
    return f"{type(module).__name__}({summary})" if summary else type(module).__name__


def collect_bundle(
    root: str | Path = ".", checkpoint: str | Path | None = None
) -> ModelBundle:
    """Find a checkpoint and everything that should travel with it.

    Args:
        root: directory to search when ``checkpoint`` is not given.
        checkpoint: an explicit path, which skips the search.

    Raises:
        CheckpointNotFound: when nothing suitable exists.
    """
    if checkpoint is not None:
        path = Path(checkpoint).expanduser()
        if not path.is_file():
            raise CheckpointNotFound(f"{path} does not exist")
        found = _describe(path)
    else:
        found = latest_checkpoint(root)

    companions, config = find_companions(found)
    directory = found.path.parent
    tokenizer = [p for p in companions if _is_tokenizer(p)]
    other = [p for p in companions if not _is_tokenizer(p)]

    manifest = read_manifest(directory / "manifest.json") or read_manifest(found.path)
    return ModelBundle(
        checkpoint=found,
        config=config,
        tokenizer_files=tokenizer,
        companion_files=other,
        manifest=manifest,
    )


def _is_tokenizer(path: Path) -> bool:
    """Return whether a file belongs to the tokenizer rather than the model."""
    lowered = path.name.lower()
    return any(marker in lowered for marker in ("tokenizer", "vocab", "merges", "special_tokens"))