from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class SkillNode:
    skill_id: str
    name: str
    category: str = "general"
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.skill_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SkillNode):
            return NotImplemented
        return self.skill_id == other.skill_id


class SkillGraph:
    def __init__(self):
        self._nodes: Dict[str, SkillNode] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._reverse_dependencies: Dict[str, List[str]] = {}

    def add_skill(self, skill: SkillNode) -> None:
        if skill.skill_id in self._nodes:
            raise ValueError(f"Skill {skill.skill_id} already exists")
        self._nodes[skill.skill_id] = skill
        self._dependencies[skill.skill_id] = list(skill.prerequisites)
        for prereq in skill.prerequisites:
            if prereq not in self._reverse_dependencies:
                self._reverse_dependencies[prereq] = []
            self._reverse_dependencies[prereq].append(skill.skill_id)

    def remove_skill(self, skill_id: str) -> None:
        if skill_id not in self._nodes:
            raise KeyError(f"Skill {skill_id} not found")
        for prereq in self._dependencies[skill_id]:
            if prereq in self._reverse_dependencies:
                self._reverse_dependencies[prereq].remove(skill_id)
        for dependent in self._reverse_dependencies.get(skill_id, []):
            self._dependencies[dependent].remove(skill_id)
        del self._nodes[skill_id]
        del self._dependencies[skill_id]
        if skill_id in self._reverse_dependencies:
            del self._reverse_dependencies[skill_id]

    def add_dependency(self, skill_id: str, prerequisite_id: str) -> None:
        if skill_id not in self._nodes:
            raise KeyError(f"Skill {skill_id} not found")
        if prerequisite_id not in self._nodes:
            raise KeyError(f"Prerequisite {prerequisite_id} not found")
        if prerequisite_id not in self._dependencies[skill_id]:
            self._dependencies[skill_id].append(prerequisite_id)
            if prerequisite_id not in self._reverse_dependencies:
                self._reverse_dependencies[prerequisite_id] = []
            self._reverse_dependencies[prerequisite_id].append(skill_id)

    def remove_dependency(self, skill_id: str, prerequisite_id: str) -> None:
        if skill_id not in self._dependencies or prerequisite_id not in self._dependencies[skill_id]:
            raise KeyError(f"Dependency from {skill_id} to {prerequisite_id} not found")
        self._dependencies[skill_id].remove(prerequisite_id)
        self._reverse_dependencies[prerequisite_id].remove(skill_id)

    def get_prerequisites(self, skill_id: str) -> List[str]:
        if skill_id not in self._nodes:
            raise KeyError(f"Skill {skill_id} not found")
        return list(self._dependencies[skill_id])

    def get_dependents(self, skill_id: str) -> List[str]:
        if skill_id not in self._nodes:
            raise KeyError(f"Skill {skill_id} not found")
        return list(self._reverse_dependencies.get(skill_id, []))

    def is_ready(self, skill_id: str, mastered_skills: Set[str]) -> bool:
        if skill_id not in self._nodes:
            raise KeyError(f"Skill {skill_id} not found")
        return all(prereq in mastered_skills for prereq in self._dependencies[skill_id])

    def topological_sort(self) -> List[str]:
        visited: Set[str] = set()
        temp_visited: Set[str] = set()
        result: List[str] = []

        def visit(node_id: str) -> None:
            if node_id in temp_visited:
                raise ValueError("Cycle detected in skill graph")
            if node_id in visited:
                return
            temp_visited.add(node_id)
            for prereq in self._dependencies[node_id]:
                visit(prereq)
            temp_visited.remove(node_id)
            visited.add(node_id)
            result.append(node_id)

        for node_id in self._nodes:
            visit(node_id)

        return result

    def get_available_skills(self, mastered_skills: Set[str]) -> List[str]:
        available = []
        for skill_id in self._nodes:
            if skill_id not in mastered_skills and self.is_ready(skill_id, mastered_skills):
                available.append(skill_id)
        return available

    def get_skill(self, skill_id: str) -> SkillNode:
        if skill_id not in self._nodes:
            raise KeyError(f"Skill {skill_id} not found")
        return self._nodes[skill_id]

    def all_skills(self) -> List[SkillNode]:
        return list(self._nodes.values())
