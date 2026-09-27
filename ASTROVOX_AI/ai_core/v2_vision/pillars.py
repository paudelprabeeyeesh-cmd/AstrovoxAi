"""AI strategic pillars."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing: List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIStrategicPillar:
    pillar_id: str
    name: str
    description: str
    goals: List[str] = field(default_factory=list)


@dataclass
class AIStrategicGoal:
    goal_id: str
    pillar_id: str
    description: str
    kpis: List[str] = field(default_factory=list)


class AIPillarManager:
    def __init__(self) -> None:
        self._pillars: Dict[str, AIStrategicPillar] = {}

    def add_pillar(self, pillar: AIStrategicPillar) -> None:
        self._pillars[pillar.pillar_id] = pillar

    def get_pillar(self, pillar_id: str) -> Optional[AIStrategicPillar]:
        return self._pillars.get(pillar_id)


ai_pillar_manager = AIPillarManager()
