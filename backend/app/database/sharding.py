"""Sharding strategies and routing."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShardConfig:
    shard_id: str
    database_name: str
    key_range: Optional[tuple[Any, Any]] = None


ShardKey = Callable[[Dict[str, Any]], str]


def hash_shard_key(key: str, num_shards: int) -> int:
    return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % num_shards


def range_shard_key(value: Any, shard_ranges: List[tuple[Any, Any]]) -> int:
    for idx, (low, high) in enumerate(shard_ranges):
        if low <= value <= high:
            return idx
    raise ValueError(f"Value {value} does not fall within any shard range")


class ShardRouter:
    def __init__(
        self,
        shards: Dict[str, ShardConfig],
        shard_key_fn: Optional[ShardKey] = None,
    ):
        self._shards = shards
        self._shard_key_fn = shard_key_fn or (lambda data: hash_shard_key(str(data.get("id")), len(shards)))
        self._shard_map: Dict[int, str] = {idx: shard.shard_id for idx, (_, shard) in enumerate(sorted(shards.items(), key=lambda x: x[0]))}

    def resolve(self, data: Dict[str, Any]) -> str:
        shard_index = self._shard_key_fn(data)
        shard_id = self._shard_map.get(shard_index)
        if shard_id is None:
            raise ValueError(f"No shard mapped to index {shard_index}")
        return shard_id

    def get_shards(self) -> Dict[str, ShardConfig]:
        return dict(self._shards)


class ShardManager:
    def __init__(self, router: ShardRouter):
        self.router = router
        self._shard_data: Dict[str, list[Dict[str, Any]]] = {shard.shard_id: [] for shard in router.get_shards().values()}

    def add_shard(self, shard: ShardConfig) -> None:
        self._shard_data[shard.shard_id] = []

    def insert(self, record: Dict[str, Any]) -> str:
        shard_id = self.router.resolve(record)
        self._shard_data[shard_id].append(record)
        logger.debug("Inserted record into shard %s", shard_id)
        return shard_id

    def query(self, predicate: Callable[[Dict[str, Any]], bool]) -> list[Dict[str, Any]]:
        results = []
        for records in self._shard_data.values():
            results.extend([r for r in records if predicate(r)])
        return results

    def rebalance(self, target_shards: int) -> None:
        logger.info("Rebalancing to %s shards", target_shards)
        all_records = [record for records in self._shard_data.values() for record in records]
        self._shard_data = {f"shard_{i}": [] for i in range(target_shards)}
        router = ShardRouter(
            {f"shard_{i}": ShardConfig(shard_id=f"shard_{i}", database_name=f"shard_{i}") for i in range(target_shards)},
        )
        for record in all_records:
            shard_id = router.resolve(record)
            self._shard_data[shard_id].append(record)
