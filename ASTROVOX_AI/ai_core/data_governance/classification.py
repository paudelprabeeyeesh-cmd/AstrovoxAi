"""AI data classifier."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIClassificationRule:
    rule_id: str
    name: str
    pattern: str
    classification: str
    confidence: float = 1.0


class AIDataClassifier:
    def __init__(self) -> None:
        self._rules: Dict[str, AIClassificationRule] = {}

    def add_rule(self, rule: AIClassificationRule) -> None:
        self._rules[rule.rule_id] = rule

    def classify(self, data: str) -> str:
        for rule in self._rules.values():
            if rule.pattern in data:
                return rule.classification
        return "unclassified"


ai_data_classifier = AIDataClassifier()
