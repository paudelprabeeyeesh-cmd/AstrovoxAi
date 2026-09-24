from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Entity:
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


class EntityRegistry:
    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._index_type: Dict[str, List[str]] = {}
        self._index_property: Dict[str, Dict[str, List[str]]] = {}

    def register(self, entity_id: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> Entity:
        if entity_id in self._entities:
            raise ValueError(f"Entity already registered: {entity_id}")
        entity = Entity(id=entity_id, type=entity_type, properties=properties if properties is not None else {})
        self._entities[entity_id] = entity
        self._index_type.setdefault(entity_type, []).append(entity_id)
        for key, value in entity.properties.items():
            self._index_property.setdefault(key, {}).setdefault(str(value), []).append(entity_id)
        return entity

    def unregister(self, entity_id: str) -> None:
        entity = self._entities.pop(entity_id, None)
        if entity is None:
            return
        type_list = self._index_type.get(entity.type)
        if type_list and entity_id in type_list:
            type_list.remove(entity_id)
        for key, value in entity.properties.items():
            prop_map = self._index_property.get(key)
            if prop_map:
                id_list = prop_map.get(str(value))
                if id_list and entity_id in id_list:
                    id_list.remove(entity_id)

    def get(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def query_by_type(self, entity_type: str) -> List[Entity]:
        ids = self._index_type.get(entity_type, [])
        return [self._entities[eid] for eid in ids if eid in self._entities]

    def query_by_property(self, property_name: str, property_value: Any) -> List[Entity]:
        id_list = self._index_property.get(property_name, {}).get(str(property_value), [])
        return [self._entities[eid] for eid in id_list if eid in self._entities]

    def list_all(self) -> List[Entity]:
        return list(self._entities.values())

    def clear(self) -> None:
        self._entities.clear()
        self._index_type.clear()
        self._index_property.clear()
