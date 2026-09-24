import hashlib
import random
from typing import Any, Dict, List, Tuple


class Sharder:
    def __init__(self, num_shards: int = 4, shard_key: str = "id") -> None:
        self._num_shards = num_shards
        self._shard_key = shard_key

    def shard_of(self, record: Dict[str, Any]) -> int:
        key = record.get(self._shard_key)
        digest = hashlib.md5(str(key).encode()).hexdigest()
        return int(digest, 16) % self._num_shards

    def shard_range(self, shard_id: int) -> Tuple[int, int]:
        low = shard_id * (2**32 // self._num_shards)
        high = ((shard_id + 1) * (2**32 // self._num_shards)) - 1
        return low, high


class ReplicaSet:
    def __init__(self, primary: str, replicas: List[str]) -> None:
        self.primary = primary
        self.replicas = replicas
        self._lag: Dict[str, float] = {r: 0.0 for r in replicas}

    def read(self, consistency: str = "eventual") -> str:
        if consistency == "strong":
            return self.primary
        return random.choice([self.primary] + self.replicas)

    def write(self) -> str:
        return self.primary

    def report_lag(self, node: str, lag_seconds: float) -> None:
        self._lag[node] = lag_seconds


class Partitioner:
    def __init__(self, strategy: str = "hash") -> None:
        self.strategy = strategy

    def partition(self, key: str, num_partitions: int) -> int:
        if self.strategy == "hash":
            return int(hashlib.md5(key.encode()).hexdigest(), 16) % num_partitions
        if self.strategy == "range":
            return ord(key[0]) % num_partitions if key else 0
        return 0
