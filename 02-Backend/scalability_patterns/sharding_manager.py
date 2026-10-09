import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Shard:
    id: int
    range_start: int
    range_end: int
    nodes: List[str] = field(default_factory=list)
    status: str = "active"


class ShardingManager:
    def __init__(self, num_shards: int = 4, shard_key: str = "id") -> None:
        self._num_shards = num_shards
        self._shard_key = shard_key
        self._shards: List[Shard] = []
        self._lock = threading.Lock()
        for shard_id in range(num_shards):
            low = shard_id * (2**32 // num_shards)
            high = ((shard_id + 1) * (2**32 // num_shards)) - 1
            self._shards.append(Shard(id=shard_id, range_start=low, range_end=high))

    def shard_of(self, record: Dict[str, Any]) -> int:
        key = record.get(self._shard_key)
        digest = hashlib.md5(str(key).encode()).hexdigest()
        return int(digest, 16) % self._num_shards

    def shard_range(self, shard_id: int) -> Tuple[int, int]:
        shard = self._shards[shard_id]
        return shard.range_start, shard.range_end

    def assign_node(self, shard_id: int, node: str) -> None:
        with self._lock:
            self._shards[shard_id].nodes.append(node)

    def remove_node(self, shard_id: int, node: str) -> None:
        with self._lock:
            self._shards[shard_id].nodes = [
                n for n in self._shards[shard_id].nodes if n != node
            ]

    def get_shard(self, shard_id: int) -> Shard:
        return self._shards[shard_id]

    def all_shards(self) -> List[Shard]:
        return list(self._shards)

    def shard_for_node(self, node: str) -> Optional[int]:
        for shard in self._shards:
            if node in shard.nodes:
                return shard.id
        return None
