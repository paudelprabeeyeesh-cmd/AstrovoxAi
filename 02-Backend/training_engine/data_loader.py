import json
import os
import random
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple


class DataLoader:
    def __init__(self, data: Optional[List[Any]] = None, batch_size: int = 32, shuffle: bool = False):
        self.data = list(data) if data is not None else []
        self.batch_size = int(batch_size)
        self.shuffle = bool(shuffle)

    def __len__(self) -> int:
        return (len(self.data) + self.batch_size - 1) // self.batch_size

    def __iter__(self) -> Iterator[List[Any]]:
        indices = list(range(len(self.data)))
        if self.shuffle:
            random.shuffle(indices)
        for i in range(0, len(self.data), self.batch_size):
            yield [self.data[idx] for idx in indices[i : i + self.batch_size]]

    def add(self, item: Any) -> None:
        self.data.append(item)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump({"data": self.data, "batch_size": self.batch_size, "shuffle": self.shuffle}, f)

    @classmethod
    def load(cls, path: str) -> "DataLoader":
        with open(path, "r") as f:
            payload = json.load(f)
        return cls(data=payload["data"], batch_size=payload["batch_size"], shuffle=payload.get("shuffle", False))
