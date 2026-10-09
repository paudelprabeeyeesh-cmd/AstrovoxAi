from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class EnvironmentState:
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    properties: Dict[str, Dict[str, float]] = field(default_factory=dict)
    time_step: int = 0


class EnvironmentSimulator:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._properties: Dict[str, Dict[str, float]] = {}
        self._history: List[EnvironmentState] = []
        self._time_step: int = 0
        self._callbacks: List[Callable[[EnvironmentSimulator], None]] = []

    def register_entity(self, entity_id: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        if entity_id in self._entities:
            raise ValueError(f"Entity already exists: {entity_id}")
        self._entities[entity_id] = attributes if attributes is not None else {}
        self._properties.setdefault(entity_id, {})

    def remove_entity(self, entity_id: str) -> None:
        self._entities.pop(entity_id, None)
        self._properties.pop(entity_id, None)

    def set_property(self, entity_id: str, property_name: str, value: float) -> None:
        if entity_id not in self._properties:
            self._properties[entity_id] = {}
        self._properties[entity_id][property_name] = value
        self._entities[entity_id][property_name] = value

    def get_property(self, entity_id: str, property_name: str, default: Optional[float] = None) -> Optional[float]:
        return self._properties.get(entity_id, {}).get(property_name, default)

    def add_callback(self, callback: Callable[[EnvironmentSimulator], None]) -> None:
        self._callbacks.append(callback)

    def step(self) -> EnvironmentState:
        for callback in self._callbacks:
            callback(self)
        self._time_step += 1
        state = self._snapshot()
        self._history.append(state)
        return state

    def reset(self) -> None:
        self._entities.clear()
        self._properties.clear()
        self._history.clear()
        self._time_step = 0

    def state(self) -> EnvironmentState:
        return self._snapshot()

    def _snapshot(self) -> EnvironmentState:
        return EnvironmentState(
            entities={k: dict(v) for k, v in self._entities.items()},
            properties={k: dict(v) for k, v in self._properties.items()},
            time_step=self._time_step,
        )

    def entities(self) -> List[str]:
        return list(self._entities.keys())

    def history(self) -> List[EnvironmentState]:
        return list(self._history)
