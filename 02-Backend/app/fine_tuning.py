import os
import json
import tempfile
import logging
from datetime import datetime, timezone
from openai import OpenAI

from repositories.database.client import get_db

logger = logging.getLogger(__name__)


class FineTuningService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required for fine-tuning")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def export_labeled_data(self, user_id: str, limit: int = 5000) -> str:
        cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=30)).isoformat()
        with get_db() as conn:
            rows = conn.execute("""
                SELECT prompt, response, model, metadata, rating, correction, tokens
                FROM interactions
                WHERE user_id = ? AND created_at >= ? AND rating IS NOT NULL AND rating >= 4
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, cutoff, limit)).fetchall()
            interactions = [dict(r) for r in rows]

        if not interactions:
            raise ValueError(f"No labeled interactions found for user {user_id}")

        fd, path = tempfile.mkstemp(suffix=".jsonl", prefix=f"finetune_{user_id}_")
        os.close(fd)

        with open(path, "w", encoding="utf-8") as f:
            for item in interactions:
                messages = [
                    {"role": "user", "content": item["prompt"]},
                ]
                if item.get("correction"):
                    messages.append({"role": "assistant", "content": item["correction"]})
                else:
                    messages.append({"role": "assistant", "content": item["response"]})

                entry = {"messages": messages}
                if item.get("metadata"):
                    entry["metadata"] = item["metadata"]
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(f"Exported {len(interactions)} interactions for user {user_id} to {path}")
        return path

    def validate_jsonl(self, file_path: str) -> bool:
        errors = []
        with open(file_path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {lineno}: Invalid JSON - {e}")
                    continue

                if "messages" not in entry:
                    errors.append(f"Line {lineno}: Missing 'messages' key")
                    continue

                if not isinstance(entry["messages"], list):
                    errors.append(f"Line {lineno}: 'messages' must be a list")
                    continue

                if len(entry["messages"]) < 2:
                    errors.append(f"Line {lineno}: Need at least 2 messages")

                for msg_idx, msg in enumerate(entry["messages"]):
                    if "role" not in msg or "content" not in msg:
                        errors.append(f"Line {lineno}, message {msg_idx}: Missing 'role' or 'content'")

                if "metadata" in entry and not isinstance(entry["metadata"], dict):
                    errors.append(f"Line {lineno}: 'metadata' must be a dict")

        if errors:
            for e in errors:
                logger.error(f"JSONL validation error: {e}")
            return False
        return True

    def create_fine_tuning_job(self, model: str, training_file: str, validation_file: str | None = None) -> str:
        if not self._get_client().api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        with open(training_file, "rb") as tf:
            training = self._get_client().files.create(file=tf, purpose="fine-tune")

        file_id = training.id

        if validation_file:
            with open(validation_file, "rb") as vf:
                validation = self._get_client().files.create(file=vf, purpose="fine-tune")
            validation_id = validation.id
        else:
            validation_id = None

        job = self._get_client().fine_tuning.jobs.create(
            training_file=file_id,
            model=model,
            validation_file=validation_id,
        )

        logger.info(f"Created fine-tuning job {job.id}")
        return job.id

    def check_job_status(self, job_id: str) -> dict:
        job = self._get_client().fine_tuning.jobs.retrieve(job_id)
        return {
            "id": job.id,
            "status": job.status,
            "model": job.model,
            "fine_tuned_model": job.fine_tuned_model,
            "created_at": job.created_at,
            "finished_at": job.finished_at,
            "trained_tokens": job.trained_tokens,
        }

    def deploy_model(self, job_id: str) -> str:
        job = self._get_client().fine_tuning.jobs.retrieve(job_id)
        if job.status != "succeeded":
            raise ValueError(f"Job {job_id} not succeeded: {job.status}")
        if not job.fine_tuned_model:
            raise ValueError(f"Job {job_id} has no fine-tuned model")
        return job.fine_tuned_model
