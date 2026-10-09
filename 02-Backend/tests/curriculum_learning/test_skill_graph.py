import pytest
from curriculum_learning.skill_graph import SkillGraph, SkillNode


class TestSkillGraph:
    def test_add_skill(self):
        sg = SkillGraph()
        skill = SkillNode(skill_id="s1", name="Skill 1")
        sg.add_skill(skill)
        assert sg.get_skill("s1").name == "Skill 1"

    def test_add_duplicate_skill_raises(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        with pytest.raises(ValueError, match="already exists"):
            sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))

    def test_remove_skill(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.remove_skill("s1")
        with pytest.raises(KeyError, match="not found"):
            sg.get_skill("s1")

    def test_add_dependency(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2"))
        sg.add_dependency("s2", "s1")
        assert sg.get_prerequisites("s2") == ["s1"]

    def test_remove_dependency(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2"))
        sg.add_dependency("s2", "s1")
        sg.remove_dependency("s2", "s1")
        assert sg.get_prerequisites("s2") == []

    def test_add_dependency_missing_skill_raises(self):
        sg = SkillGraph()
        with pytest.raises(KeyError):
            sg.add_dependency("s2", "s1")

    def test_get_dependents(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2"))
        sg.add_dependency("s2", "s1")
        assert sg.get_dependents("s1") == ["s2"]

    def test_is_ready_with_mastered(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2", prerequisites=["s1"]))
        assert sg.is_ready("s2", {"s1"}) is True
        assert sg.is_ready("s2", set()) is False

    def test_is_ready_missing_skill_raises(self):
        sg = SkillGraph()
        with pytest.raises(KeyError):
            sg.is_ready("missing", set())

    def test_topological_sort(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2", prerequisites=["s1"]))
        sg.add_skill(SkillNode(skill_id="s3", name="Skill 3", prerequisites=["s2"]))
        order = sg.topological_sort()
        assert order.index("s1") < order.index("s2")
        assert order.index("s2") < order.index("s3")

    def test_topological_sort_cycle_raises(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2", prerequisites=["s1"]))
        sg.add_dependency("s1", "s2")
        with pytest.raises(ValueError, match="Cycle detected"):
            sg.topological_sort()

    def test_get_available_skills(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2", prerequisites=["s1"]))
        available = sg.get_available_skills(set())
        assert available == ["s1"]
        available = sg.get_available_skills({"s1"})
        assert available == ["s2"]

    def test_all_skills(self):
        sg = SkillGraph()
        sg.add_skill(SkillNode(skill_id="s1", name="Skill 1"))
        sg.add_skill(SkillNode(skill_id="s2", name="Skill 2"))
        skills = sg.all_skills()
        assert len(skills) == 2
        assert {s.skill_id for s in skills} == {"s1", "s2"}
