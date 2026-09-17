"""Backward compatibility guarantees."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BackwardCompatibility:
    def __init__(self) -> None:
        self.contracts: dict[str, dict[str, Any]] = {
            "v1": {"status": "supported", "sunset": None},
            "v0": {"status": "deprecated", "sunset": "2027-03-01"},
        }

    def supported(self, version: str) -> bool:
        return version in self.contracts
