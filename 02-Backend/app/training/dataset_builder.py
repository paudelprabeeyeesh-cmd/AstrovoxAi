"""
Dataset builder for training data preparation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DatasetSample:
    prompt: str
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetManifest:
    name: str
    samples: List[DatasetSample]
    version: str = "1.0.0"
    hash: Optional[str] = None

    def __post_init__(self):
        if self.hash is None:
            content = json.dumps([s.__dict__ for s in self.samples], sort_keys=True)
            self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]


class DatasetBuilder:
    def __init__(self, name: str, max_samples: int = 10000):
        self.name = name
        self.max_samples = max_samples
        self._samples: List[DatasetSample] = []
        self._seen_hashes: set = set()

    def add_sample(self, prompt: str, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if len(self._samples) >= self.max_samples:
            return
        key = hashlib.md5(f"{prompt}\x00{response}".encode()).hexdigest()
        if key in self._seen_hashes:
            return
        self._seen_hashes.add(key)
        self._samples.append(DatasetSample(prompt=prompt, response=response, metadata=metadata or {}))

    def add_from_file(self, path: str, parser: Optional[Callable[[str], Iterable[DatasetSample]]] = None) -> int:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if parser:
                    for sample in parser(line):
                        self.add_sample(sample.prompt, sample.response, sample.metadata)
                        count += 1
                else:
                    try:
                        entry = json.loads(line)
                        if "messages" in entry:
                            msgs = entry["messages"]
                            if len(msgs) >= 2:
                                self.add_sample(msgs[-2]["content"], msgs[-1]["content"], entry.get("metadata", {}))
                                count += 1
                    except json.JSONDecodeError:
                        continue
        return count

    def add_from_directory(self, directory: str, extensions: Optional[List[str]] = None) -> int:
        extensions = extensions or [".txt", ".md", ".json"]
        count = 0
        for ext in extensions:
            for file_path in Path(directory).rglob(f"*{ext}"):
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    self.add_sample(text[:1024], text[1024:2048], {"source": str(file_path), "ext": ext})
                    count += 1
                except Exception:
                    continue
        return count

    def filter(self, predicate: Callable[[DatasetSample], bool]) -> None:
        self._samples = [s for s in self._samples if predicate(s)]

    def shuffle(self, seed: int = 42) -> None:
        import random
        random.Random(seed).shuffle(self._samples)

    def build(self, train_split: float = 0.9, seed: int = 42) -> Tuple["DatasetManifest", "DatasetManifest"]:
        self.shuffle(seed)
        split = int(len(self._samples) * train_split)
        train = DatasetManifest(name=f"{self.name}-train", samples=self._samples[:split])
        val = DatasetManifest(name=f"{self.name}-val", samples=self._samples[split:])
        return train, val

    def save(self, directory: str) -> Dict[str, str]:
        Path(directory).mkdir(parents=True, exist_ok=True)
        train, val = self.build()
        paths = {}
        for manifest, suffix in [(train, "train"), (val, "val")]:
            path = os.path.join(directory, f"{self.name}_{suffix}.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for sample in manifest.samples:
                    f.write(json.dumps({"prompt": sample.prompt, "response": sample.response, "metadata": sample.metadata}, ensure_ascii=False) + "\n")
            paths[suffix] = path
        logger.info("Saved dataset %s to %s", self.name, directory)
        return paths

    @property
    def samples(self) -> List[DatasetSample]:
        return list(self._samples)

    def __len__(self) -> int:
        return len(self._samples)
