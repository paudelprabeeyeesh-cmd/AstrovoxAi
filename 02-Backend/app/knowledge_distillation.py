"""
Model distillation with knowledge transfer and temperature scaling.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class KnowledgeDistiller:
    def __init__(self, teacher_model: nn.Module, student_model: nn.Module, temperature: float = 2.0, alpha: float = 0.5):
        self.teacher_model = teacher_model
        self.student_model = student_model
        self.temperature = temperature
        self.alpha = alpha

<<<<<<< HEAD
    def distillation_loss(self, student_logits: torch.Tensor, teacher_logits: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        soft_targets = F.softmax(teacher_logits / self.temperature, dim=-1)
        soft_prob = F.log_softmax(student_logits / self.temperature, dim=-1)
        soft_loss = -(soft_targets * soft_prob).sum(dim=-1).mean() * (self.temperature ** 2)
        hard_loss = F.cross_entropy(student_logits, labels)
        total_loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
        return total_loss, {'soft_loss': soft_loss.item(), 'hard_loss': hard_loss.item(), 'total_loss': total_loss.item()}

    def train_step(self, input_ids: torch.Tensor, labels: torch.Tensor, optimizer: torch.optim.Optimizer) -> Dict[str, float]:
        self.teacher_model.eval()
        self.student_model.train()
        with torch.no_grad():
            teacher_logits = self.teacher_model(input_ids)
        student_logits = self.student_model(input_ids)
        loss, metrics = self.distillation_loss(student_logits, teacher_logits, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        return metrics
=======
    def generate_training_data(self, teacher_model: str, prompts: List[str], num_samples: int = 100) -> List[Dict[str, Any]]:
        if not self._client:
            raise RuntimeError("OpenAI API key is required for teacher model. Set OPENAI_API_KEY.")
        training_data = []
        for prompt in prompts:
            for _ in range(num_samples):
                try:
                    response = self._client.chat.completions.create(
                        model=teacher_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=512,
                    )
                    content = response.choices[0].message.content
                    training_data.append({"prompt": prompt, "completion": content})
                except Exception as _e:  # noqa: BLE001
                    logger.error(f"Failed to generate training sample: {_e}")
                    continue
        return training_data

    def train_student_model(self, teacher_model: str, student_model: str, training_data: List[Dict[str, Any]]) -> str:
        f"distilled-{student_model.replace('/', '-')}"
        logger.info(f"Training student model {student_model} with {len(training_data)} samples from {teacher_model}")
        try:
            from app.fine_tuning import FineTuningService
            service = FineTuningService()
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
                for item in training_data:
                    f.write(json.dumps({"messages": [{"role": "user", "content": item["prompt"]}, {"role": "assistant", "content": item["completion"]}]}) + "\n")
                tmp_path = f.name
            job_id = service.create_fine_tuning_job(model=student_model, training_file=tmp_path)
            logger.info(f"Created fine-tuning job {job_id} for distilled model")
            return job_id
        except Exception as _e:  # noqa: BLE001
            logger.error(f"Failed to train student model: {_e}")
            raise

    def evaluate_distillation(self, student_model: str, test_set: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("OpenAI API key is required for evaluation. Set OPENAI_API_KEY.")
        results = []
        for item in test_set:
            try:
                response = self._client.chat.completions.create(
                    model=student_model,
                    messages=[{"role": "user", "content": item["prompt"]}],
                    temperature=0.0,
                    max_tokens=256,
                )
                predicted = response.choices[0].message.content
                reference = item.get("completion", "")
                results.append({"prompt": item["prompt"], "predicted": predicted, "reference": reference})
            except Exception as _e:  # noqa: BLE001
                logger.error(f"Evaluation failed for prompt: {_e}")
                continue
        total = len(results)
        if total == 0:
            return {"accuracy": 0.0, "samples": 0, "results": []}
        exact_matches = sum(1 for r in results if r["predicted"].strip() == r["reference"].strip())
        accuracy = exact_matches / total
        return {"accuracy": accuracy, "samples": total, "results": results}
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
