import logging
import os
import json
from typing import List, Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class KnowledgeDistillationService:
    def __init__(self, teacher_api_key: str = ""):
        self._api_key = teacher_api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

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
                except Exception as e:
                    logger.error(f"Failed to generate training sample: {e}")
                    continue
        return training_data

    def train_student_model(self, teacher_model: str, student_model: str, training_data: List[Dict[str, Any]]) -> str:
        model_id = f"distilled-{student_model.replace('/', '-')}"
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
        except Exception as e:
            logger.error(f"Failed to train student model: {e}")
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
            except Exception as e:
                logger.error(f"Evaluation failed for prompt: {e}")
                continue
        total = len(results)
        if total == 0:
            return {"accuracy": 0.0, "samples": 0, "results": []}
        exact_matches = sum(1 for r in results if r["predicted"].strip() == r["reference"].strip())
        accuracy = exact_matches / total
        return {"accuracy": accuracy, "samples": total, "results": results}
