import pytest

from lifelong_learning.skill_transfer import Skill, SkillTransfer


class TestSkillTransfer:
    def test_register_skill(self):
        st = SkillTransfer()
        skill = st.register_skill("s1", "python", proficiency=0.8, source_task="task1")
        assert skill.skill_id == "s1"
        assert skill.proficiency == 0.8
        assert skill.source_task == "task1"

    def test_register_duplicate_raises(self):
        st = SkillTransfer()
        st.register_skill("s1", "python")
        with pytest.raises(ValueError):
            st.register_skill("s1", "python2")

    def test_transfer_skill(self):
        st = SkillTransfer()
        st.register_skill("s1", "python", proficiency=0.8)
        transferred = st.transfer_skill("s1", "task2", boost=0.1)
        assert transferred is not None
        assert transferred.proficiency == 0.9
        assert transferred.metadata["target_task"] == "task2"

    def test_transfer_skill_unknown_returns_none(self):
        st = SkillTransfer()
        assert st.transfer_skill("unknown", "task2") is None

    def test_get_transferable_skills(self):
        st = SkillTransfer()
        st.register_skill("s1", "python", source_task="task1")
        st.register_skill("s2", "java", source_task="task2")
        transferable = st.get_transferable_skills("task1")
        assert len(transferable) == 1
        assert transferable[0].skill_id == "s2"

    def test_compute_transfer_benefit(self):
        st = SkillTransfer(similarity_threshold=0.5)
        st.register_skill("s1", "python", proficiency=0.8)
        benefit = st.compute_transfer_benefit("s1", "task2")
        assert benefit == 0.4

    def test_compute_transfer_benefit_unknown(self):
        st = SkillTransfer()
        assert st.compute_transfer_benefit("unknown", "task2") == 0.0

    def test_get_stats(self):
        st = SkillTransfer()
        st.register_skill("s1", "python", proficiency=0.8)
        st.transfer_skill("s1", "task2")
        stats = st.get_stats()
        assert stats["total_skills"] == 2
        assert stats["total_transfers"] == 1
