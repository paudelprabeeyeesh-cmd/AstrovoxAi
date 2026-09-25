import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProceduralMemoryService:
    def add_skill(self, skill: dict[str, Any]) -> None:
        logger.info(f"Skill added: {skill.get('name')}")

    def chain(self, skill_ids: list[str]) -> dict[str, Any]:
        return {"chain_id": "->".join(skill_ids), "skills": skill_ids}
