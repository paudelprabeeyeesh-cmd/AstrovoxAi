"""Tests for Knowledge Distillation with KL divergence."""

import numpy as np
import pytest
import torch
import torch.nn as nn

from quantization.knowledge_distillation import DistillationConfig, DistillationLoss, KnowledgeDistillationTrainer


class DummyTeacher(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(16, 4)

    def forward(self, x):
        return self.fc(x)


class DummyStudent(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(16, 4)

    def forward(self, x):
        return self.fc(x)


class TestDistillationLoss:
    def test_output_shape(self):
        loss_fn = DistillationLoss(temperature=2.0, alpha=0.5)
        student_logits = torch.randn(4, 10)
        teacher_logits = torch.randn(4, 10)
        labels = torch.randint(0, 10, (4,))
        loss = loss_fn(student_logits, teacher_logits, labels)
        assert loss.shape == ()

    def test_scalar_loss(self):
        loss_fn = DistillationLoss()
        student_logits = torch.randn(2, 8)
        teacher_logits = torch.randn(2, 8)
        labels = torch.randint(0, 8, (2,))
        loss = loss_fn(student_logits, teacher_logits, labels)
        assert loss.dim() == 0

    def test_kl_divergence_component(self):
        loss_fn = DistillationLoss(temperature=1.0, alpha=0.0)
        student_logits = torch.randn(2, 8)
        teacher_logits = torch.randn(2, 8)
        labels = torch.randint(0, 8, (2,))
        loss = loss_fn(student_logits, teacher_logits, labels)
        assert torch.isfinite(loss)

    def test_cross_entropy_component(self):
        loss_fn = DistillationLoss(temperature=1.0, alpha=1.0)
        student_logits = torch.randn(2, 8)
        teacher_logits = torch.randn(2, 8)
        labels = torch.randint(0, 8, (2,))
        loss = loss_fn(student_logits, teacher_logits, labels)
        assert torch.isfinite(loss)

    def test_numpy_kl_equivalence(self):
        loss_fn = DistillationLoss(temperature=2.0, alpha=0.5)
        student_logits = torch.randn(4, 8)
        teacher_logits = torch.randn(4, 8)
        labels = torch.randint(0, 8, (4,))
        loss = loss_fn(student_logits, teacher_logits, labels)
        T = 2.0
        soft_loss = torch.nn.functional.kl_div(
            torch.nn.functional.log_softmax(student_logits / T, dim=-1),
            torch.nn.functional.softmax(teacher_logits / T, dim=-1),
            reduction="batchmean",
        ) * (T ** 2)
        hard_loss = torch.nn.functional.cross_entropy(student_logits, labels)
        expected = 0.5 * soft_loss + 0.5 * hard_loss
        np.testing.assert_allclose(loss.item(), expected.item(), rtol=1e-5)


class TestKnowledgeDistillationTrainer:
    def test_train_step(self):
        teacher = DummyTeacher()
        student = DummyStudent()
        config = DistillationConfig()
        trainer = KnowledgeDistillationTrainer(teacher, student, config)
        batch = {
            "input_ids": torch.randn(2, 8, 16),
            "labels": torch.randint(0, 4, (2, 8)),
        }
        loss = trainer.train_step(batch)
        assert isinstance(loss, float)
        assert np.isfinite(loss)

    def test_teacher_eval_student_train(self):
        teacher = DummyTeacher()
        student = DummyStudent()
        config = DistillationConfig()
        trainer = KnowledgeDistillationTrainer(teacher, student, config)
        assert not teacher.training
        assert student.training
