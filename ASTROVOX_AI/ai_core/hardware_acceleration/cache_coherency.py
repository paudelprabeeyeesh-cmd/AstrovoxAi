from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Set
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class CacheCoherencyProtocol:
    def __init__(self, protocol_type: str = "msi"):
        self.protocol_type = protocol_type
        self.cache_states: Dict[str, str] = {}
        self.directory: Dict[str, Set[str]] = {}

    def read(self, address: str, cache_id: str) -> str:
        state = self.cache_states.get(address, "I")
        if state == "I":
            self._request_shared(address, cache_id)
        return self.cache_states.get(address, "I")

    def write(self, address: str, cache_id: str) -> None:
        if self.cache_states.get(address) in ("S", "I"):
            self._request_exclusive(address, cache_id)
        self.cache_states[address] = "M"

    def invalidate(self, address: str, requester: str) -> None:
        if address in self.cache_states and self.cache_states[address] == "M":
            for owner in self.directory.get(address, set()):
                if owner != requester:
                    self.cache_states[address] = "I"
                    self.directory.get(address, set()).discard(owner)

    def _request_shared(self, address: str, cache_id: str) -> None:
        self.cache_states[address] = "S"
        self.directory.setdefault(address, set()).add(cache_id)

    def _request_exclusive(self, address: str, cache_id: str) -> None:
        self.invalidate(address, cache_id)
        self.cache_states[address] = "E"
        self.directory[address] = {cache_id}


class DirectoryBasedCoherency:
    def __init__(self, num_nodes: int = 8):
        self.num_nodes = num_nodes
        self.directory: Dict[str, Dict[str, Any]] = {}
        self.local_caches: Dict[str, Dict[str, Any]] = {f"node_{i}": {} for i in range(num_nodes)}

    def access(self, address: str, node_id: str, is_write: bool = False) -> Any:
        entry = self.directory.get(address)
        if entry is None:
            self.directory[address] = {"state": "U", "owner": node_id, "sharers": set()}
            if is_write:
                self.directory[address]["state"] = "M"
            return None
        if is_write and entry["state"] != "M":
            self._invalidate_others(address, node_id)
            entry["state"] = "M"
            entry["owner"] = node_id
        return self.local_caches[node_id].get(address)

    def _invalidate_others(self, address: str, owner: str) -> None:
        for node, cache in self.local_caches.items():
            if node != owner and address in cache:
                del cache[address]


class SnoopingCoherency:
    def __init__(self, num_caches: int = 4):
        self.num_caches = num_caches
        self.bus = BusInterface()
        self.caches: List[Dict[str, Any]] = [{} for _ in range(num_caches)]

    def read(self, address: str, cache_id: int) -> Any:
        if address in self.caches[cache_id]:
            return self.caches[cache_id][address]
        for i, cache in enumerate(self.caches):
            if i != cache_id and address in cache:
                data = cache[address]
                self.caches[cache_id][address] = data
                return data
        return None

    def write(self, address: str, cache_id: int, data: Any) -> None:
        self.caches[cache_id][address] = data
        for i, cache in enumerate(self.caches):
            if i != cache_id and address in cache:
                del cache[address]


class BusInterface:
    def __init__(self):
        self.listeners: List[Callable] = []

    def broadcast(self, message: Dict[str, Any]) -> None:
        for listener in self.listeners:
            listener(message)

    def register(self, listener: Callable) -> None:
        self.listeners.append(listener)
