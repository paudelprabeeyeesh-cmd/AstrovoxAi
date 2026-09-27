"""Database infrastructure management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatabaseInstance:
    instance_id: str
    engine: str
    version: str
    size: str
    region: str


class DatabaseInfrastructureManager:
    def __init__(self) -> None:
        self._instances: Dict[str, DatabaseInstance] = {}

    def provision(self, instance: DatabaseInstance) -> DatabaseInstance:
        self._instances[instance.instance_id] = instance
        return instance

    def get_instance(self, instance_id: str) -> Optional[DatabaseInstance]:
        return self._instances.get(instance_id)


db_infra_manager = DatabaseInfrastructureManager()
