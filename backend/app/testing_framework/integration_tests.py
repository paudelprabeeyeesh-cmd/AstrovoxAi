"""Integration testing framework."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestCase:
    test_id: str
    name: str
    setup: Optional[Callable[[], Any]] = None
    func: Optional[Callable[[], Any]] = None
    teardown: Optional[Callable[[], Any]] = None


class IntegrationTestSuite:
    def __init__(self, name: str) -> None:
        self.suite_id = name
        self.name = name
        self.cases: List[IntegrationTestCase] = []

    def add_case(self, case: IntegrationTestCase) -> None:
        self.cases.append(case)


integration_test_suite = IntegrationTestSuite("integration")
