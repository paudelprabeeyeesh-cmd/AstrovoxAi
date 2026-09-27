from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]

try:
    from datasets import load_dataset
except Exception:  # pragma: no cover - optional dependency
    load_dataset = None  # type: ignore[assignment]


def _load_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _load_parquet(path: str, columns: list[str] | None = None) -> Iterator[dict]:
    if pd is None:
        raise ImportError("pandas is required to read parquet files. Install it with: pip install pandas pyarrow")
    df = pd.read_parquet(path, columns=columns)
    for record in df.to_dict(orient="records"):
        yield record


def _load_hf(dataset_name: str, config_name: str | None, split: str, columns: list[str] | None, streaming: bool) -> Iterator[dict]:
    if load_dataset is None:
        raise ImportError("datasets is required. Install it with: pip install datasets")
    ds = load_dataset(dataset_name, config_name, split=split, streaming=streaming)
    for example in ds:
        yield example


class MemmapDataset:
    def __init__(self, path: str, dtype: str = "uint32", mmap_mode: str = "r"):
        self.path = Path(path)
        self.mmap = np.memmap(self.path, dtype=dtype, mode=mmap_mode)

    def __len__(self) -> int:
        return int(self.mmap.shape[0])

    def __getitem__(self, idx: int) -> int:
        return int(self.mmap[idx])

    def __iter__(self) -> Iterator[int]:
        for i in range(len(self)):
            yield int(self.mmap[i])

    def close(self):
        if hasattr(self, "mmap"):
            del self.mmap


class StreamingDataset:
    def __init__(
        self,
        source: str,
        fmt: str = "jsonl",
        text_column: str = "text",
        columns: list[str] | None = None,
        transform: Callable[[dict], dict] | None = None,
        limit: int | None = None,
    ):
        self.source = source
        self.fmt = fmt
        self.text_column = text_column
        self.columns = columns
        self.transform = transform
        self.limit = limit
        self._count = 0

    def _iter_source(self) -> Iterator[dict]:
        if self.fmt == "jsonl":
            yield from _load_jsonl(self.source)
        elif self.fmt in {"parquet", "pq"}:
            yield from _load_parquet(self.source, columns=self.columns)
        elif self.fmt == "hf":
            yield from _load_hf(self.source, None, "train", self.columns, streaming=True)
        else:
            raise ValueError(f"Unsupported format: {self.fmt}")

    def __iter__(self) -> Iterator[dict]:
        for record in self._iter_source():
            if self.transform:
                record = self.transform(record)
            self._count += 1
            yield record
            if self.limit is not None and self._count >= self.limit:
                break

    def __len__(self) -> int:
        if self.limit is not None:
            return self.limit
        if self.fmt in {"jsonl"}:
            with open(self.source, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        return 0


def load_dataset_iterator(
    path: str,
    fmt: str | None = None,
    text_column: str = "text",
    columns: list[str] | None = None,
    transform: Callable[[dict], dict] | None = None,
    limit: int | None = None,
) -> Iterator[dict]:
    path = str(path)
    if fmt is None:
        ext = Path(path).suffix.lower()
        if ext == ".jsonl":
            fmt = "jsonl"
        elif ext in {".parquet", ".pq"}:
            fmt = "parquet"
        elif path.startswith("hf://") or path.startswith("hf:"):
            fmt = "hf"
        else:
            fmt = "jsonl"

    dataset = StreamingDataset(
        source=path,
        fmt=fmt,
        text_column=text_column,
        columns=columns,
        transform=transform,
        limit=limit,
    )
    yield from dataset
