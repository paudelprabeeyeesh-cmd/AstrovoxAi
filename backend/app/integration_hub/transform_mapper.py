"""Data transformation mapping for integrations."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MappingRule:
    rule_id: str
    source_field: str
    target_field: str
    transform: Optional[Callable[[Any], Any]] = None
    default: Any = None


class TransformMapper:
    def __init__(self) -> None:
        self._rules: Dict[str, List[MappingRule]] = {}

    def add_mapping(self, integration_id: str, rule: MappingRule) -> None:
        self._rules.setdefault(integration_id, []).append(rule)

    def map(self, integration_id: str, source: Dict[str, Any]) -> Dict[str, Any]:
        rules = self._rules.get(integration_id, [])
        target: Dict[str, Any] = {}
        for rule in rules:
            value = source.get(rule.source_field)
            if rule.transform and value is not None:
                try:
                    value = rule.transform(value)
                except Exception:
                    value = rule.default
            if value is not None:
                target[rule.target_field] = value
            elif rule.default is not None:
                target[rule.target_field] = rule.default
        return target


transform_mapper = TransformMapper()
