"""System prompt versioning with A/B testing and rollback support."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from repositories.database.client import get_db

from .prompt_validation import PromptTemplateValidator, PromptValidationResult

logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    id: str
    name: str
    template: str
    version: str
    description: str
    created_at: str
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)


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
