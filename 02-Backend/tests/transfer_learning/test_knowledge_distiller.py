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

    def test_custom_initialization(self):
        distiller = KnowledgeDistiller(teacher_name="t1", student_name="s1", temperature=4.0, alpha=0.8)
        assert distiller.pair.teacher_name == "t1"
        assert distiller.pair.student_name == "s1"
        assert distiller.pair.temperature == 4.0
        assert distiller.pair.alpha == 0.8

    def test_softmax_single_element(self):
        distiller = KnowledgeDistiller()
        result = distiller._softmax([2.0], 1.0)
        assert len(result) == 1
        assert math.isfinite(result[0])

    def test_softmax_zero_temperature(self):
        distiller = KnowledgeDistiller(temperature=1.0)
        result = distiller._softmax([1.0, 2.0, 3.0], 1.0)
        assert len(result) == 3
        assert math.isfinite(sum(result))

    def test_cross_entropy(self):
        distiller = KnowledgeDistiller()
        probs = [0.25, 0.25, 0.25, 0.25]
        targets = [1.0, 0.0, 0.0, 0.0]
        loss = distiller._cross_entropy(probs, targets)
        assert math.isfinite(loss)
        assert loss >= 0.0

    def test_knowledge_transfer_sequence_mismatch(self):
        distiller = KnowledgeDistiller()
        with pytest.raises(ValueError):
            distiller.knowledge_transfer([[1.0]], [[1.0], [2.0]])

    def test_knowledge_transfer_with_labels(self):
        distiller = KnowledgeDistiller()
        report = distiller.knowledge_transfer(
            [[1.0, 2.0], [0.5, 1.5]],
            [[0.8, 1.8], [0.4, 1.4]],
            labels_sequence=[[1.0, 0.0], [0.0, 1.0]],
        )
        assert report["steps"] == 2
        assert report["mean_loss"] >= 0.0
        assert "min_loss" in report
        assert "max_loss" in report

    def test_summary_with_data(self):
        distiller = KnowledgeDistiller()
        distiller.distill_step([1.0, 2.0], [0.8, 1.8])
        distiller.distill_step([2.0, 3.0], [1.5, 2.5])
        summary = distiller.summary()
        assert summary["steps"] == 2
        assert "mean_loss" in summary
        assert "last_loss" in summary

    def test_distillation_log_contents(self):
        distiller = KnowledgeDistiller()
        distiller.distill_step([1.0, 2.0], [0.8, 1.8])
        assert len(distiller.pair.distillation_log) == 1
        entry = distiller.pair.distillation_log[0]
        assert "soft_loss" in entry
        assert "hard_loss" in entry
        assert "total_loss" in entry
        assert entry["hard_loss"] == 0.0

    def test_distill_step_hard_loss(self):
        distiller = KnowledgeDistiller()
        loss = distiller.distill_step([1.0, 2.0], [0.5, 1.5], labels=[1.0, 0.0])
        assert math.isfinite(loss)
        assert len(distiller.pair.distillation_log) == 1
        assert distiller.pair.distillation_log[0]["hard_loss"] > 0.0
