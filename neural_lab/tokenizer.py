"""A deterministic character tokenizer with bounded-memory file scanning."""

from __future__ import annotations

from pathlib import Path

from .config import MAX_VOCAB_SIZE


class CharacterTokenizer:
    def __init__(self, characters: list[str]):
        if len(characters) > MAX_VOCAB_SIZE:
            raise ValueError(f"character vocabulary exceeds the {MAX_VOCAB_SIZE} character safety limit")
        if not characters or len(set(characters)) != len(characters):
            raise ValueError("vocabulary must contain unique characters")
        self.characters = tuple(characters)
        self._ids = {char: index for index, char in enumerate(self.characters)}
        self.token_count: int | None = None

    @classmethod
    def from_file(cls, path: str | Path, max_file_bytes: int = 16 * 1024 * 1024) -> CharacterTokenizer:
        source = Path(path)
        size = source.stat().st_size
        if size == 0:
            raise ValueError("dataset is empty")
        if size > max_file_bytes:
            raise ValueError(f"dataset is {size} bytes; configured limit is {max_file_bytes}")
        characters: set[str] = set()
        token_count = 0
        with source.open("r", encoding="utf-8", errors="strict") as stream:
            while chunk := stream.read(8192):
                characters.update(chunk)
                if len(characters) > MAX_VOCAB_SIZE:
                    raise ValueError(f"character vocabulary exceeds the {MAX_VOCAB_SIZE} character safety limit")
                token_count += len(chunk)
        if not characters:
            raise ValueError("dataset contains no text")
        tokenizer = cls(sorted(characters))
        tokenizer.token_count = token_count
        return tokenizer

    @property
    def vocab_size(self) -> int:
        return len(self.characters)

    def encode(self, text: str) -> list[int]:
        try:
            return [self._ids[char] for char in text]
        except KeyError as exc:
            raise ValueError("text contains a character outside the fitted vocabulary") from exc

    def decode(self, token_ids: list[int]) -> str:
        if any(index < 0 or index >= self.vocab_size for index in token_ids):
            raise ValueError("token id is outside the vocabulary")
        return "".join(self.characters[index] for index in token_ids)

    def to_dict(self) -> dict[str, list[str]]:
        return {"characters": list(self.characters)}

    @classmethod
    def from_dict(cls, value: dict[str, list[str]]) -> CharacterTokenizer:
        return cls(value["characters"])
