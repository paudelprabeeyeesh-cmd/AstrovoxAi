import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    skill_id: str
    name: str
    procedure: list[str]
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)


class ProceduralMemory:
    def __init__(self):
        self.skills: dict[str, Skill] = {}
        self.chains: dict[str, list[str]] = {}

    def add_skill(self, skill: Skill) -> None:
        self.skills[skill.skill_id] = skill

    def chain(self, skill_ids: list[str]) -> dict[str, Any]:
        chain_id = "->".join(skill_ids)
        self.chains[chain_id] = skill_ids
        return {"chain_id": chain_id, "skills": skill_ids}
