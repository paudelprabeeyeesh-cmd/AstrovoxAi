"""Bounded, local-only text dataset storage for Neural Lab experiments."""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .config import MAX_VOCAB_SIZE

MAX_DATASET_BYTES = 16 * 1024 * 1024
MAX_NOTE_LENGTH = 2000


class DatasetStore:
    """Store explicitly selected UTF-8 text files under one approved directory."""

    def __init__(self, root: str | Path, max_file_bytes: int = MAX_DATASET_BYTES):
        if not 1 <= max_file_bytes <= MAX_DATASET_BYTES:
            raise ValueError(f"max_file_bytes must be between 1 and {MAX_DATASET_BYTES}")
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    def _metadata_path(self, dataset_id: str) -> Path:
        if len(dataset_id) != 64 or any(char not in "0123456789abcdef" for char in dataset_id):
            raise ValueError("invalid dataset id")
        path = (self.root / f"{dataset_id}.json").resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("dataset id resolves outside the approved directory")
        return path

    def add_file(
        self,
        source: str | Path,
        *,
        provenance: str = "User-provided local file",
        license_note: str = "Unspecified; verify permission before use",
        preview_characters: int = 500,
    ) -> dict:
        source_path = Path(source).expanduser().resolve(strict=True)
        if not source_path.is_file() or source_path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("select a local .txt or .md file")
        if not 0 <= preview_characters <= 4096:
            raise ValueError("preview_characters must be between 0 and 4096")
        if not provenance.strip() or not license_note.strip():
            raise ValueError("provenance and license_note must be non-empty")
        if len(provenance) > MAX_NOTE_LENGTH or len(license_note) > MAX_NOTE_LENGTH:
            raise ValueError("provenance and license_note must be at most 2000 characters")
        size = source_path.stat().st_size
        if size == 0:
            raise ValueError("dataset is empty")
        if size > self.max_file_bytes:
            raise ValueError(f"dataset is {size} bytes; limit is {self.max_file_bytes}")

        digest = hashlib.sha256()
        decoder = codecs.getincrementaldecoder("utf-8")("strict")
        chars = 0
        lines = 0
        unique: set[str] = set()
        preview: list[str] = []
        has_non_whitespace = False
        fd, staging_name = tempfile.mkstemp(prefix="dataset-", suffix=".tmp", dir=self.root)
        staging = Path(staging_name)
        try:
            with os.fdopen(fd, "wb") as target, source_path.open("rb") as input_file:
                while chunk := input_file.read(64 * 1024):
                    digest.update(chunk)
                    target.write(chunk)
                    text = decoder.decode(chunk)
                    chars += len(text)
                    lines += text.count("\n")
                    has_non_whitespace |= bool(text.strip())
                    unique.update(text)
                    if len(unique) > MAX_VOCAB_SIZE:
                        raise ValueError(f"dataset contains more than {MAX_VOCAB_SIZE} unique characters")
                    if sum(map(len, preview)) < preview_characters:
                        remaining = preview_characters - sum(map(len, preview))
                        preview.append(text[:remaining])
                tail = decoder.decode(b"", final=True)
                chars += len(tail)
                lines += tail.count("\n")
                has_non_whitespace |= bool(tail.strip())
                unique.update(tail)
                if len(unique) > MAX_VOCAB_SIZE:
                    raise ValueError(f"dataset contains more than {MAX_VOCAB_SIZE} unique characters")
                if sum(map(len, preview)) < preview_characters:
                    remaining = preview_characters - sum(map(len, preview))
                    preview.append(tail[:remaining])
            if chars == 0 or not has_non_whitespace:
                raise ValueError("dataset contains no non-whitespace text")
            dataset_id = digest.hexdigest()
            metadata_path = self._metadata_path(dataset_id)
            content_path = self.root / f"{dataset_id}.txt"
            if metadata_path.exists() and content_path.exists():
                staging.unlink(missing_ok=True)
                return json.loads(metadata_path.read_text(encoding="utf-8"))
            os.replace(staging, content_path)
            metadata = {
                "schema_version": 1,
                "dataset_id": dataset_id,
                "original_name": source_path.name,
                "stored_file": content_path.name,
                "sha256": dataset_id,
                "size_bytes": size,
                "character_count": chars,
                "line_count": lines,
                "unique_character_count": len(unique),
                "preview": "".join(preview),
                "provenance": provenance.strip(),
                "license_note": license_note.strip(),
                "created_at": datetime.now(UTC).isoformat(),
            }
            temporary_metadata = metadata_path.with_suffix(".json.tmp")
            temporary_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary_metadata, metadata_path)
            return metadata
        finally:
            staging.unlink(missing_ok=True)

    def list_datasets(self) -> list[dict]:
        records = []
        for metadata_path in self.root.glob("*.json"):
            try:
                record = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            stored_file = record.get("stored_file")
            if record.get("dataset_id") != metadata_path.stem or not isinstance(stored_file, str):
                continue
            stored_path = (self.root / stored_file).resolve()
            if stored_path.is_relative_to(self.root) and stored_path.is_file():
                records.append(record)
        return sorted(records, key=lambda item: item["created_at"])

    def get_path(self, dataset_id: str) -> Path:
        metadata = json.loads(self._metadata_path(dataset_id).read_text(encoding="utf-8"))
        if metadata.get("dataset_id") != dataset_id or metadata.get("stored_file") != f"{dataset_id}.txt":
            raise ValueError("dataset metadata is invalid")
        path = (self.root / metadata["stored_file"]).resolve(strict=True)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError("stored dataset path is invalid")
        return path

    def delete(self, dataset_id: str, *, confirmed: bool = False) -> None:
        if not confirmed:
            raise PermissionError("dataset deletion requires confirmed=True")
        metadata_path = self._metadata_path(dataset_id)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("dataset_id") != dataset_id or metadata.get("stored_file") != f"{dataset_id}.txt":
            raise ValueError("dataset metadata is invalid")
        content_path = (self.root / metadata["stored_file"]).resolve()
        if not content_path.is_relative_to(self.root):
            raise ValueError("stored dataset path resolves outside the approved directory")
        content_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
