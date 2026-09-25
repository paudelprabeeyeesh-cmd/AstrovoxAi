import uuid
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from repositories.database.client import get_db

logger = logging.getLogger(__name__)


class PromptVersion:
    def __init__(self, id: str, name: str, template: str, version: str, description: str, created_at: str):
        self.id = id
        self.name = name
        self.template = template
        self.version = version
        self.description = description
        self.created_at = created_at


class PromptVersionManager:
    def __init__(self):
        self.prompts_dir = "app/prompts"
        os.makedirs(self.prompts_dir, exist_ok=True)

    def create_prompt(self, name: str, template: str, version: str, description: str) -> PromptVersion:
        prompt_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """INSERT INTO prompt_versions (id, name, template, version, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (prompt_id, name, template, version, description, created_at),
            )
            conn.commit()
        return PromptVersion(prompt_id, name, template, version, description, created_at)

    def get_prompt(self, name: str, version: Optional[str] = None) -> Optional[PromptVersion]:
        with get_db() as conn:
            if version:
                row = conn.execute(
                    "SELECT id, name, template, version, description, created_at FROM prompt_versions WHERE name = ? AND version = ?",
                    (name, version),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT id, name, template, version, description, created_at FROM prompt_versions
                       WHERE name = ? ORDER BY created_at DESC LIMIT 1""",
                    (name,),
                ).fetchone()
        if not row:
            return None
        return PromptVersion(row["id"], row["name"], row["template"], row["version"], row["description"], row["created_at"])

    def list_prompts(self) -> list:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT DISTINCT name FROM prompt_versions ORDER BY name ASC"""
            ).fetchall()
            return [r["name"] for r in rows]

    def compare_versions(self, name: str, v1: str, v2: str) -> dict:
        prompt1 = self.get_prompt(name, v1)
        prompt2 = self.get_prompt(name, v2)
        if not prompt1 or not prompt2:
            raise ValueError("Prompt version not found")
        return {
            "name": name,
            "version_1": v1,
            "version_2": v2,
            "template_1": prompt1.template,
            "template_2": prompt2.template,
            "description_1": prompt1.description,
            "description_2": prompt2.description,
        }

    def rollback_prompt(self, name: str, version: str) -> PromptVersion:
        target = self.get_prompt(name, version)
        if not target:
            raise ValueError("Prompt version not found")
        new_version = f"{version}_rollback_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        return self.create_prompt(name, target.template, new_version, f"Rollback to {version}")
