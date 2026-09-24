from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Skill:
    skill_id: str
    name: str
    proficiency: float = 0.0
    source_task: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillTransfer:
    def __init__(self, similarity_threshold: float = 0.5) -> None:
        self.similarity_threshold = similarity_threshold
        self._skills: Dict[str, Skill] = {}
        self._transfers: List[Dict[str, Any]] = []

    def register_skill(
        self,
        skill_id: str,
        name: str,
        proficiency: float = 0.0,
        source_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Skill:
        if skill_id in self._skills:
            raise ValueError(f"Skill {skill_id} already registered")
        skill = Skill(
            skill_id=skill_id,
            name=name,
            proficiency=proficiency,
            source_task=source_task,
            metadata=metadata or {},
        )
        self._skills[skill_id] = skill
        return skill

    def transfer_skill(
        self, skill_id: str, target_task: str, boost: float = 0.1
    ) -> Optional[Skill]:
        if skill_id not in self._skills:
            return None
        skill = self._skills[skill_id]
        target_key = f"{skill_id}:{target_task}"
        if target_key not in self._skills:
            transferred = Skill(
                skill_id=target_key,
                name=skill.name,
                proficiency=min(1.0, skill.proficiency + boost),
                source_task=skill.source_task,
                metadata={"transferred_from": skill_id, "target_task": target_task},
            )
            self._skills[target_key] = transferred
            self._transfers.append({
                "skill_id": skill_id,
                "target_task": target_task,
                "boost": boost,
                "new_proficiency": transferred.proficiency,
            })
            return transferred
        existing = self._skills[target_key]
        existing.proficiency = min(1.0, existing.proficiency + boost)
        self._transfers.append({
            "skill_id": skill_id,
            "target_task": target_task,
            "boost": boost,
            "new_proficiency": existing.proficiency,
        })
        return existing

    def get_transferable_skills(self, target_task: str) -> List[Skill]:
        return [s for s in self._skills.values() if s.source_task != target_task]

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def compute_transfer_benefit(self, source_skill_id: str, target_task: str) -> float:
        source = self._skills.get(source_skill_id)
        if source is None:
            return 0.0
        benefit = source.proficiency * self.similarity_threshold
        return min(1.0, benefit)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._skills)
        avg_proficiency = (
            sum(s.proficiency for s in self._skills.values()) / total if total else 0.0
        )
        return {
            "total_skills": total,
            "average_proficiency": round(avg_proficiency, 4),
            "total_transfers": len(self._transfers),
        }
