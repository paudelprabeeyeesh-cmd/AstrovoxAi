"""Data transformation engine with rule-based and ML-powered transformations."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TransformationRule:
    rule_id: str
    name: str
    input_columns: List[str]
    output_column: str
    transform_fn: Callable[[Dict[str, Any]], Any]
    description: str = ""


class TransformationEngine:
    def __init__(self) -> None:
        self._rules: List[TransformationRule] = []

    def add_rule(self, rule: TransformationRule) -> None:
        self._rules.append(rule)

    def apply(self, record: Dict[str, Any]) -> Dict[str, Any]:
        output = dict(record)
        for rule in self._rules:
            try:
                output[rule.output_column] = rule.transform_fn({k: record.get(k) for k in rule.input_columns})
            except Exception as exc:
                logger.exception("transformation rule %s failed", rule.rule_id)
                output[rule.output_column] = None
        return output

    def apply_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.apply(record) for record in records]

    def remove_rule(self, rule_id: str) -> None:
        self._rules = [r for r in self._rules if r.rule_id != rule_id]


transformation_engine = TransformationEngine()
