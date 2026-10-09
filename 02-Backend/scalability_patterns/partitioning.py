import hashlib
from typing import Tuple


class Partitioner:
    def __init__(self, strategy: str = "hash") -> None:
        self.strategy = strategy

    def partition(self, key: str, num_partitions: int) -> int:
        if self.strategy == "hash":
            return int(hashlib.md5(key.encode()).hexdigest(), 16) % num_partitions
        if self.strategy == "range":
            return ord(key[0]) % num_partitions if key else 0
        return 0

    def bounds(
        self, partition_id: int, num_partitions: int, key_space: int = 2**32
    ) -> Tuple[int, int]:
        low = partition_id * (key_space // num_partitions)
        high = ((partition_id + 1) * (key_space // num_partitions)) - 1
        return low, high
