import numpy as np
from adaptive_learning.curriculum_learning import CurriculumScheduler, CurriculumConfig, KnowledgeDistiller


class TestCurriculumScheduler:
    def test_initialization(self):
        cs = CurriculumScheduler()
        assert cs.config.start_difficulty == 0.1
        assert cs.config.end_difficulty == 1.0
        assert cs.epoch == 0

    def test_step_linear(self):
        cs = CurriculumScheduler(CurriculumConfig(start_difficulty=0.0, end_difficulty=1.0, warmup_epochs=2))
        for _ in range(5):
            cs.step()
        assert cs.current_difficulty > 0.0
        assert len(cs.difficulty_history) == 5

    def test_filter_samples(self):
        cs = CurriculumScheduler()
        cs.current_difficulty = 0.5
        x = np.random.randn(10, 4)
        y = np.random.randn(10)
        difficulty = np.array([0.1, 0.2, 0.3, 0.6, 0.7, 0.8, 0.4, 0.9, 0.5, 0.55])
        fx, fy = cs.filter_samples(x, y, difficulty)
        assert fx.shape[0] == fy.shape[0]
        assert fx.shape[0] <= 10

    def test_difficulty_report(self):
        cs = CurriculumScheduler()
        cs.step()
        report = cs.get_difficulty_report()
        assert "epoch" in report
        assert "current_difficulty" in report
        assert report["epoch"] == 1


class TestKnowledgeDistiller:
    def test_initialization(self):
        kd = KnowledgeDistiller(temperature=2.0)
        assert kd.temperature == 2.0
        assert len(kd.teacher_logits) == 0

    def test_distill(self):
        kd = KnowledgeDistiller(temperature=2.0)
        teacher = np.random.randn(4, 3)
        student = np.random.randn(4, 3)
        loss = kd.distill(teacher, student)
        assert isinstance(loss, float)
        assert loss >= 0.0
        assert len(kd.teacher_logits) == 1

    def test_distill_with_targets(self):
        kd = KnowledgeDistiller()
        teacher = np.random.randn(4, 3)
        student = np.random.randn(4, 3)
        targets = np.array([0, 1, 2, 1])
        loss = kd.distill(teacher, student, targets=targets)
        assert isinstance(loss, float)

    def test_get_distillation_stats(self):
        kd = KnowledgeDistiller()
        teacher = np.random.randn(4, 3)
        student = np.random.randn(4, 3)
        kd.distill(teacher, student)
        stats = kd.get_distillation_stats()
        assert stats["num_distillations"] == 1
        assert stats["temperature"] == 2.0
