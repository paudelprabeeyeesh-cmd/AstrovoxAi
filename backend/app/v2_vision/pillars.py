"""Strategic pillars for v2.0."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategicPillar:
    pillar_id: str
    name: str
    description: str
    goals: List[str] = field(default_factory=list)


@dataclass
class StrategicGoal:
    goal_id: str
    pillar_id: str
    description: str
    kpis: List[str] = field(default_factory=list)


class PillarManager:
    def __init__(self) -> None:
        self._pillars: Dict[str, StrategicPillar] = {}

    def add_pillar(self, pillar: StrategicPillar) -> None:
        self._pillars[pillar.pillar_id] = pillar

    def get_pillar(self, pillar_id: str) -> Optional[StrategicPillar]:
        return self._pillars.get(pillar_id)


pillar_manager = PillarManager()
