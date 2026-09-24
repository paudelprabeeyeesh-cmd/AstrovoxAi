from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TeacherStudentPair:
    teacher_name: str
    student_name: str
    temperature: float = 2.0
    alpha: float = 0.5
    distillation_log: List[Dict[str, Any]] = field(default_factory=list)


class KnowledgeDistiller:
    def __init__(
        self,
        teacher_name: str = "teacher",
        student_name: str = "student",
        temperature: float = 2.0,
        alpha: float = 0.5,
    ) -> None:
        self.pair = TeacherStudentPair(
            teacher_name=teacher_name,
            student_name=student_name,
            temperature=temperature,
            alpha=alpha,
        )

    def _softmax(self, logits: List[float], temperature: float) -> List[float]:
        if not logits:
            return []
        scaled = [v / temperature for v in logits]
        max_v = max(scaled)
        exps = [__import__("math").exp(v - max_v) for v in scaled]
        total = sum(exps)
        if total == 0:
            return [1.0 / len(logits)] * len(logits)
        return [e / total for e in exps]

    def _cross_entropy(self, probs: List[float], targets: List[float]) -> float:
        eps = 1e-9
        return -sum(
            t * __import__("math").log(max(p, eps))
            for p, t in zip(probs, targets)
        ) / max(len(probs), 1)

    def distill_step(
        self,
        teacher_logits: List[float],
        student_logits: List[float],
        labels: Optional[List[float]] = None,
    ) -> float:
        if len(teacher_logits) != len(student_logits):
            raise ValueError("teacher_logits and student_logits must have the same length")
        soft_targets = self._softmax(teacher_logits, self.pair.temperature)
        soft_loss = self._cross_entropy(self._softmax(student_logits, self.pair.temperature), soft_targets)
        hard_loss = 0.0
        if labels is not None:
            if len(labels) != len(student_logits):
                raise ValueError("labels length must match student_logits length")
            hard_loss = self._cross_entropy(self._softmax(student_logits, 1.0), labels)
        loss = self.pair.alpha * soft_loss + (1.0 - self.pair.alpha) * hard_loss
        self.pair.distillation_log.append(
            {
                "soft_loss": soft_loss,
                "hard_loss": hard_loss,
                "total_loss": loss,
            }
        )
        return loss

    def knowledge_transfer(
        self,
        teacher_logits_sequence: List[List[float]],
        student_logits_sequence: List[List[float]],
        labels_sequence: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        if len(teacher_logits_sequence) != len(student_logits_sequence):
            raise ValueError("Sequences length mismatch")
        losses: List[float] = []
        for idx, (t_logits, s_logits) in enumerate(zip(teacher_logits_sequence, student_logits_sequence)):
            labels = labels_sequence[idx] if labels_sequence is not None else None
            losses.append(self.distill_step(t_logits, s_logits, labels))
        return {
            "steps": len(losses),
            "mean_loss": sum(losses) / max(len(losses), 1),
            "min_loss": min(losses) if losses else 0.0,
            "max_loss": max(losses) if losses else 0.0,
        }

    def summary(self) -> Dict[str, Any]:
        if not self.pair.distillation_log:
            return {"steps": 0}
        losses = [entry["total_loss"] for entry in self.pair.distillation_log]
        return {
            "steps": len(losses),
            "mean_loss": sum(losses) / len(losses),
            "last_loss": losses[-1],
        }
