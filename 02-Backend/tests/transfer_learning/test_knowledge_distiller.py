import math

import pytest

from transfer_learning.knowledge_distiller import KnowledgeDistiller, TeacherStudentPair


class TestTeacherStudentPair:
    def test_pair_initialization(self):
        pair = TeacherStudentPair(teacher_name="t", student_name="s")
        assert pair.teacher_name == "t"
        assert pair.student_name == "s"
        assert pair.temperature == 2.0
        assert pair.alpha == 0.5
        assert pair.distillation_log == []


class TestKnowledgeDistiller:
    def test_distill_step(self):
        distiller = KnowledgeDistiller()
        teacher_logits = [1.0, 2.0, 3.0]
        student_logits = [1.0, 2.0, 3.0]
        loss = distiller.distill_step(teacher_logits, student_logits)
        assert math.isfinite(loss)
        assert len(distiller.pair.distillation_log) == 1

    def test_distill_step_with_labels(self):
        distiller = KnowledgeDistiller()
        loss = distiller.distill_step([1.0, 2.0], [0.5, 1.5], labels=[1.0, 0.0])
        assert math.isfinite(loss)

    def test_distill_step_length_mismatch(self):
        distiller = KnowledgeDistiller()
        with pytest.raises(ValueError):
            distiller.distill_step([1.0, 2.0], [1.0])

    def test_knowledge_transfer(self):
        distiller = KnowledgeDistiller()
        report = distiller.knowledge_transfer(
            [[1.0, 2.0], [0.5, 1.5]],
            [[0.8, 1.8], [0.4, 1.4]],
        )
        assert report["steps"] == 2
        assert report["mean_loss"] >= 0.0

    def test_summary(self):
        distiller = KnowledgeDistiller()
        assert distiller.summary()["steps"] == 0
        distiller.distill_step([1.0, 2.0], [0.8, 1.8])
        summary = distiller.summary()
        assert summary["steps"] == 1
